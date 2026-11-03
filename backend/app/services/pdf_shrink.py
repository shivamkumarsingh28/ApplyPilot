"""Reduce a PDF's size without extracting its text or changing its meaning.

Most big application PDFs are big because of embedded scanned images. We
re-encode only those images (downscale + JPEG) and compress content streams.
Text, vector pages and page layout stay exactly as they were. If we cannot do
better we return the original bytes (or the losslessly compressed version).
"""

from __future__ import annotations

import io

from pypdf import PdfReader, PdfWriter

# (max image side in px, JPEG quality) tried in order until the target is met.
_LADDERS = [(1600, 75), (1200, 65), (900, 55), (700, 45)]


def _reencode_images(writer: PdfWriter, max_side: int, quality: int) -> None:
    for page in writer.pages:
        for image in page.images:
            try:
                pil = image.image
                if max(pil.size) <= max_side and pil.mode in ("RGB", "L"):
                    # Already small: only rewrite if re-encoding clearly wins.
                    buf = io.BytesIO()
                    pil.save(buf, format="JPEG", quality=quality, optimize=True)
                    if len(buf.getvalue()) >= len(image.data):
                        continue
                resized = pil.convert("RGB")
                if max(resized.size) > max_side:
                    resized.thumbnail((max_side, max_side))
                # image.replace needs the NameObject key, not the ImageFile.
                image.replace(resized, quality=quality)
            except Exception:
                continue  # unsupported image (JBIG2 etc.): keep the original


def compress_pdf(data: bytes, max_kb: int | None = None) -> tuple[bytes, dict]:
    """Return (bytes, info) with the PDF compressed, ideally to <= max_kb.

    info: {"original_kb", "final_kb", "pages", "within", "method"}
    """
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise ValueError("This PDF is password-protected. Remove the password first.")
    original_kb = len(data) / 1024

    def build(reencode: tuple[int, int] | None) -> bytes:
        writer = PdfWriter()
        writer.append(reader)
        try:
            writer.compress_identical_objects()
        except Exception:
            pass
        if reencode:
            _reencode_images(writer, *reencode)
        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()

    # Lossless pass first: many PDFs already drop 10-40% from stream compression.
    best = build(None)
    method = "stream compression"
    target = (max_kb * 1024) if max_kb else None
    if target and len(best) > target:
        for step in _LADDERS:
            candidate = build(step)
            if len(candidate) < len(best):
                best, method = candidate, f"images resized (max {step[0]}px, quality {step[1]})"
            if len(best) <= target:
                break
    if len(best) >= len(data):
        best, method = data, "already optimised (returned unchanged)"
    return best, {
        "original_kb": round(original_kb, 1),
        "final_kb": round(len(best) / 1024, 1),
        "pages": len(reader.pages),
        "within": len(best) <= target if target else True,
        "method": method,
    }
