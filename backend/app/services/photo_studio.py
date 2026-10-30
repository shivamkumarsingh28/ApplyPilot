"""Photo and signature studio.

Turns a phone selfie or a photo of a signed paper into a file that satisfies a
portal's exact rules: pixel size, KB range, background colour, format.

Photo pipeline:   detect face -> crop to the target aspect ratio -> remove the
                  background (SAM 3.1 or GrabCut) -> resize -> compress into the KB range.
Signature:        flatten lighting -> find ink -> crop tight -> centre on white -> compress.

Every step is reported in `report["checks"]` so the user can see why a file passes.
"""

from __future__ import annotations

import io
import struct
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageOps

from app.services.segmenter import get_segmenter

BACKGROUNDS = {"white": (255, 255, 255), "light blue": (173, 216, 230), "blue": (70, 130, 200), "grey": (200, 200, 200), "gray": (200, 200, 200)}
MAX_INPUT_SIDE = 1800


@dataclass
class Spec:
    width: int | None = None
    height: int | None = None
    min_kb: int | None = None
    max_kb: int | None = None
    format: str = "jpg"
    background: str = "white"

    @classmethod
    def from_dict(cls, d: dict | None) -> Spec:
        d = d or {}
        return cls(d.get("width"), d.get("height"), d.get("min_kb"), d.get("max_kb"),
                   (d.get("format") or "jpg").lower().replace("jpeg", "jpg"), (d.get("background") or "white").lower())


def _load(data: bytes) -> Image.Image:
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    if max(img.size) > MAX_INPUT_SIDE:
        img.thumbnail((MAX_INPUT_SIDE, MAX_INPUT_SIDE))
    return img


def _detect_face(img: Image.Image) -> tuple[int, int, int, int] | None:
    gray = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2GRAY)
    if hasattr(cv2, "CascadeClassifier"):  # OpenCV < 5: classic Haar cascade
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(max(40, img.width // 12),) * 2)
        if len(faces) == 0:
            return None
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        return int(x), int(y), int(w), int(h)
    if hasattr(cv2, "FaceDetectorYN_create"):  # OpenCV 5 removed CascadeClassifier
        try:
            import urllib.request
            from pathlib import Path

            model = Path(__file__).with_name("face_detection_yunet_2023mar.onnx")
            if not model.exists():
                urllib.request.urlretrieve(
                    "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
                    model,
                )
            detector = cv2.FaceDetectorYN_create(str(model), "", (img.width, img.height), 0.6)
            _, faces = detector.detect(gray)
            if faces is None or len(faces) == 0:
                return None
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])[:4]
            return int(x), int(y), int(w), int(h)
        except Exception:
            return None
    return None


def _crop_box_for_face(face, aspect: float, img_size) -> tuple[int, int, int, int]:
    """Crop so the face sits in the upper-middle, with head and shoulders visible."""
    x, y, w, h = face
    crop_h = h * 2.5
    crop_w = crop_h * aspect
    cx, cy = x + w / 2, y + h * 0.95
    return int(cx - crop_w / 2), int(cy - crop_h / 2), int(cx + crop_w / 2), int(cy + crop_h / 2)


def _center_crop_box(size, aspect: float) -> tuple[int, int, int, int]:
    w, h = size
    if w / h > aspect:
        cw, ch = int(h * aspect), h
    else:
        cw, ch = w, int(w / aspect)
    left, top = (w - cw) // 2, int((h - ch) * 0.25)
    return left, top, left + cw, top + ch


def _crop_with_padding(img: Image.Image, box, fill=(255, 255, 255)) -> Image.Image:
    left, top, right, bottom = box
    canvas = Image.new("RGB", (right - left, bottom - top), fill)
    canvas.paste(img, (-left, -top))
    return canvas


def _pad_jpeg(data: bytes, target_bytes: int) -> bytes:
    """Grow a JPEG to `target_bytes` by inserting COM (comment) segments after SOI.
    The image is unchanged and still valid; this satisfies portals that demand a minimum size."""
    need = target_bytes - len(data)
    if need <= 0 or not data.startswith(b"\xff\xd8"):
        return data
    segs = b""
    while need > 0:
        chunk = min(need, 65000)
        segs += b"\xff\xfe" + struct.pack(">H", chunk + 2) + b"\x20" * (chunk - 4 if chunk > 4 else 0) + b"\x00\x00"[: min(4, chunk)]
        need -= chunk
    return data[:2] + segs + data[2:]


def _encode(img: Image.Image, fmt: str, quality: int) -> bytes:
    buf = io.BytesIO()
    if fmt == "png":
        img.save(buf, format="PNG", optimize=True)
    else:
        img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def fit_size(img: Image.Image, spec: Spec) -> tuple[bytes, dict]:
    """Encode `img` so its size lands in [min_kb, max_kb]; returns (bytes, info)."""
    fmt = "png" if spec.format == "png" else "jpg"
    lo_b = (spec.min_kb or 0) * 1024
    hi_b = (spec.max_kb or 10_000) * 1024
    if fmt == "png":
        data = _encode(img, "png", 0)
        return data, {"quality": None, "bytes": len(data), "padded": False, "within": lo_b <= len(data) <= hi_b}
    lo, hi, best = 20, 95, None
    while lo <= hi:  # binary search the highest quality that stays under the max
        q = (lo + hi) // 2
        data = _encode(img, "jpg", q)
        if len(data) <= hi_b:
            best, lo = (q, data), q + 1
        else:
            hi = q - 1
    if best is None:
        data = _encode(img, "jpg", 10)
        return data, {"quality": 10, "bytes": len(data), "padded": False, "within": len(data) <= hi_b and len(data) >= lo_b}
    q, data = best
    padded = False
    if len(data) < lo_b:
        data = _pad_jpeg(data, lo_b + 256)
        padded = True
    return data, {"quality": q, "bytes": len(data), "padded": padded, "within": lo_b <= len(data) <= hi_b}


def _report(spec: Spec, out_img: Image.Image, info: dict, extra: list[dict], warnings: list[str]) -> dict:
    checks = list(extra)
    if spec.width and spec.height:
        checks.append({"name": "Size in pixels", "ok": out_img.size == (spec.width, spec.height), "detail": f"{out_img.width}x{out_img.height} (needs {spec.width}x{spec.height})"})
    if spec.min_kb or spec.max_kb:
        kb = info["bytes"] / 1024
        checks.append({"name": "File size", "ok": info["within"], "detail": f"{kb:.1f} KB (needs {spec.min_kb or 0}-{spec.max_kb or 'any'} KB)" + (" - padded to reach the minimum" if info["padded"] else "")})
    checks.append({"name": "Format", "ok": True, "detail": spec.format.upper()})
    return {"checks": checks, "warnings": warnings, "ok": all(c["ok"] for c in checks), "bytes": info["bytes"]}


def process_photo(data: bytes, spec_dict: dict | None) -> tuple[bytes, dict]:
    spec = Spec.from_dict(spec_dict)
    img = _load(data)
    out_w = spec.width or 413
    out_h = spec.height or 531
    aspect = out_w / out_h
    warnings: list[str] = []
    checks: list[dict] = []

    face = _detect_face(img)
    if face:
        box = _crop_box_for_face(face, aspect, img.size)
        checks.append({"name": "Face detected", "ok": True, "detail": "Cropped around the face"})
    else:
        box = _center_crop_box(img.size, aspect)
        warnings.append("No face detected, so the photo was centre-cropped. Check the result before uploading.")
        checks.append({"name": "Face detected", "ok": False, "detail": "Not found"})

    cropped = _crop_with_padding(img, box)
    hint = None
    if face:
        fx, fy, fw, fh = face
        hint = (max(0, fx - box[0] - fw // 2), max(0, fy - box[1] - fh // 2), int(fw * 2), int(fh * 3))
    segmenter = get_segmenter()
    mask = segmenter.foreground_mask(cropped, hint, "person")
    mask_img = Image.fromarray(mask).filter(ImageFilter.GaussianBlur(1.5))
    bg = Image.new("RGB", cropped.size, BACKGROUNDS.get(spec.background, (255, 255, 255)))
    composed = Image.composite(cropped, bg, mask_img)
    checks.append({"name": "Background", "ok": True, "detail": f"Set to {spec.background} ({getattr(segmenter, 'last_used', segmenter.name)})"})

    out = composed.resize((out_w, out_h), Image.LANCZOS)
    payload, info = fit_size(out, spec)
    return payload, _report(spec, out, info, checks, warnings)


def process_signature(data: bytes, spec_dict: dict | None) -> tuple[bytes, dict]:
    spec = Spec.from_dict(spec_dict)
    img = _load(data)
    gray = np.array(img.convert("L")).astype(np.float32)
    k = max(31, (min(gray.shape) // 8) | 1)
    background = cv2.GaussianBlur(gray, (k, k), 0)
    flat = np.clip(gray / np.maximum(background, 1) * 255, 0, 255)  # removes shadows and uneven light
    ink = flat < 170
    warnings: list[str] = []
    if ink.mean() < 0.0005:
        warnings.append("Almost no ink was found. Use a dark pen on white paper in good light.")
        box = (0, 0, gray.shape[1], gray.shape[0])
    else:
        ys, xs = np.where(ink)
        pad = 8
        box = (max(0, xs.min() - pad), max(0, ys.min() - pad), min(gray.shape[1], xs.max() + pad), min(gray.shape[0], ys.max() + pad))
    cleaned = np.where(flat > 200, 255, flat).astype(np.uint8)
    cropped = Image.fromarray(cleaned).crop(box)

    out_w, out_h = spec.width or 300, spec.height or 100
    scale = min((out_w - 6) / cropped.width, (out_h - 6) / cropped.height)
    resized = cropped.resize((max(1, int(cropped.width * scale)), max(1, int(cropped.height * scale))), Image.LANCZOS)
    canvas = Image.new("L", (out_w, out_h), 255)
    canvas.paste(resized, ((out_w - resized.width) // 2, (out_h - resized.height) // 2))
    out = canvas.convert("RGB")
    payload, info = fit_size(out, spec)
    checks = [{"name": "Ink found", "ok": bool(ink.mean() >= 0.0005), "detail": f"{ink.mean() * 100:.2f}% of pixels"}]
    return payload, _report(spec, out, info, checks, warnings)
