"""Photo/vault media tools (Inventory groups 4 + a few of 6), by document id.

Images are never passed through the model: the tool receives an id, opens the
vault file itself, works on a COPY, and returns numbers/previews — not bytes.
Every edit saves a new application copy; originals are never modified.
"""

from __future__ import annotations

import io

from PIL import Image

from app.db.models import Document
from app.services.agents.tools import Tool, ToolContext, ToolError, _notice, needs_input
from app.services.profile_store import load_profile  # noqa: F401  (kept symmetrical with tools.py)
from app.services.storage import load_file


def _doc(ctx: ToolContext, args: dict) -> Document:
    try:
        did = int(args.get("document_id"))
    except (TypeError, ValueError):
        raise ToolError("document_id must be a number (see list_documents)") from None
    doc = ctx.db.get(Document, did)
    if doc is None or doc.user_id != ctx.user.id:
        raise ToolError("Document not found")
    return doc


def _image(ctx: ToolContext, args: dict) -> tuple[Document, Image.Image]:
    doc = _doc(ctx, args)
    if not (doc.mime or "").startswith("image/"):
        raise ToolError("That file is not an image")
    return doc, Image.open(io.BytesIO(load_file(doc.storage_path)))


def inspect_image(ctx: ToolContext, args: dict) -> dict:
    doc, img = _image(ctx, args)
    return {"document_id": doc.id, "filename": doc.filename, "width": img.width, "height": img.height,
            "format": img.format, "kb": round((doc.size or 0) / 1024, 1)}


def detect_face_tool(ctx: ToolContext, args: dict) -> dict:
    import base64  # noqa: F401

    doc, img = _image(ctx, args)
    from app.services.photo_studio import _detect_face

    face = _detect_face(img.convert("RGB"))
    if not face:
        return {"document_id": doc.id, "face_found": False, "note": "No face found. Check lighting and that the photo is upright."}
    x, y, w, h = face
    return {"document_id": doc.id, "face_found": True, "position": {"x": x, "y": y, "width": w, "height": h},
            "face_percent_of_width": round(100 * w / img.width)}


def check_photo_quality(ctx: ToolContext, args: dict) -> dict:
    import cv2
    import numpy as np

    doc, img = _image(ctx, args)
    gray = np.array(img.convert("L"))
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    bright = float(gray.mean())
    problems = []
    if blur < 60:
        problems.append("The photo looks blurry. Take it again in good light, holding the phone still.")
    if bright < 70:
        problems.append("The photo is dark. Face a window or a light.")
    if bright > 235:
        problems.append("The photo is over-bright/washed out. Move away from direct light.")
    from app.services.photo_studio import _detect_face

    face = _detect_face(img.convert("RGB"))
    if not face:
        problems.append("No face detected.")
    elif face[2] / img.width < 0.15:
        problems.append("Your face is small in the frame. Move closer.")
    return {"document_id": doc.id, "blur_score": round(blur), "brightness": round(bright),
            "problems": problems, "overall": "good" if not problems else "needs work"}


def parse_color_name(ctx: ToolContext, args: dict) -> dict:
    from app.services.colours import parse_colour

    text = str(args.get("text") or "").strip()
    if not text:
        return needs_input(["text"], {"text": "a colour name like 'light blue' or #e6f0ff"})
    parsed = parse_colour(text)
    if parsed is None:
        raise ToolError(f"I do not know the colour '{text}'. Try white, light blue, blue, grey, cream, or a #hex code.")
    rgb, label = parsed
    return {"colour": label, "rgb": list(rgb)}


def get_image_requirements(ctx: ToolContext, args: dict) -> dict:
    n = _notice(ctx, args)
    s = n.structured or {}
    kind = str(args.get("kind") or "photo")
    spec = s.get("signature_spec") if kind == "signature" else s.get("photo_spec")
    if not spec:
        raise ToolError(f"No {kind} rules could be read from this notice")
    return {"notice_id": n.id, "kind": kind, "spec": spec}


def prepare_for_notice(ctx: ToolContext, args: dict) -> dict:
    """Recipe tool: run the whole studio pipeline for a notice, save as a vault copy."""
    from app.api.routes.documents import store_document
    from app.services.photo_studio import process_photo, process_resize, process_signature

    doc, _ = _image(ctx, args)
    n = _notice(ctx, args)
    kind = str(args.get("kind") or doc.kind or "photo")
    s = n.structured or {}
    spec = dict(s.get("signature_spec") if kind == "signature" else s.get("photo_spec") or {})
    if not spec and kind == "photo":
        spec = {"width": 200, "height": 230}
    engine = process_signature if kind == "signature" else process_photo
    if args.get("resize_only"):
        engine = process_resize
        kind = "photo"
    data = load_file(doc.storage_path)
    out, report = engine(data, spec)
    fmt = "png" if spec.get("format") == "png" else "jpg"
    mime = "image/png" if fmt == "png" else "image/jpeg"
    base = (doc.filename.rsplit(".", 1)[0] or "file")[:100]
    saved = store_document(ctx.db, ctx.user, out, f"{base}_ready.{fmt}", mime, kind if kind in ("photo", "signature") else "other",
                           is_original=False, original_id=doc.id, notice_id=n.id)
    return {"notice_id": n.id, "source_document_id": doc.id, "saved_document_id": saved.id,
            "filename": saved.filename, "kb": round(len(out) / 1024, 1), "checks": report["checks"],
            "warnings": report["warnings"], "original_untouched": True}


def make_application_copy_tool(ctx: ToolContext, args: dict) -> dict:
    from app.api.routes.documents import app_ref_for, store_document

    doc = _doc(ctx, args)
    if not doc.is_original:
        raise ToolError("Only an original can be copied")
    app_id, ref = app_ref_for(ctx.db, ctx.user, args.get("notice_id"))
    copy = store_document(ctx.db, ctx.user, load_file(doc.storage_path), doc.filename, doc.mime, doc.kind,
                          is_original=False, original_id=doc.id, application_id=app_id,
                          notice_id=args.get("notice_id"), app_ref=ref, custom_kind=doc.custom_kind or "")
    return {"copy_document_id": copy.id, "app_ref": ref, "original_document_id": doc.id}


def list_application_documents(ctx: ToolContext, args: dict) -> dict:
    try:
        app_id = int(args.get("application_id"))
    except (TypeError, ValueError):
        return needs_input(["application_id"])
    rows = (ctx.db.query(Document).filter(Document.user_id == ctx.user.id, Document.application_id == app_id)
            .order_by(Document.id.desc()).all())
    originals = (ctx.db.query(Document).filter(Document.user_id == ctx.user.id, Document.is_original.is_(True))
                 .order_by(Document.id.desc()).limit(20).all())
    return {"application_id": app_id,
            "copies": [{"id": d.id, "filename": d.filename, "app_ref": d.app_ref or ""} for d in rows],
            "your_originals": [{"id": d.id, "kind": d.custom_kind or d.kind, "filename": d.filename} for d in originals]}


def get_document_info(ctx: ToolContext, args: dict) -> dict:
    doc = _doc(ctx, args)
    info = {"document_id": doc.id, "filename": doc.filename, "mime": doc.mime, "kb": round((doc.size or 0) / 1024, 1),
            "kind": doc.custom_kind or doc.kind, "is_original": doc.is_original}
    if doc.mime == "application/pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(load_file(doc.storage_path)))
            info["pages"] = len(reader.pages)
            info["has_text"] = any((p.extract_text() or "").strip() for p in reader.pages[:3])
        except Exception:
            info["pages"] = None
    return info


MEDIA_TOOLS: list[Tool] = [
    Tool("inspect_image", "Read an image's pixels, format and KB size.", {"document_id": "vault file id"}, inspect_image),
    Tool("detect_face", "Find the face in a photo and say how big it is.", {"document_id": "vault photo id"}, detect_face_tool),
    Tool("check_photo_quality", "Check a photo: blur, brightness, face size. Returns plain-language problems.",
         {"document_id": "vault photo id"}, check_photo_quality),
    Tool("parse_color_name", "Turn a colour in words ('light blue', '#e6f0ff') into its exact colour.",
         {"text": "colour words"}, parse_color_name, kind="compute"),
    Tool("get_image_requirements", "The pixel/KB/format/background rules a notice asks for (photo or signature).",
         {"notice_id": "number, optional", "kind": "photo|signature"}, get_image_requirements),
    Tool("prepare_for_notice", "Fix a vault photo/signature to a notice's rules in one step and save the result as a vault copy. The original is never changed.",
         {"document_id": "vault file id", "notice_id": "number, optional", "kind": "photo|signature", "resize_only": "true for resize-only"},
         prepare_for_notice, kind="write", confirm=True),
    Tool("make_application_copy", "Make an application copy of a vault original.", {"document_id": "vault file id", "notice_id": "number, optional"},
         make_application_copy_tool, kind="write", confirm=True),
    Tool("list_application_documents", "Files made for one application, plus your originals.", {"application_id": "number"}, list_application_documents),
    Tool("get_document_info", "Pages, size and type of a vault file.", {"document_id": "vault file id"}, get_document_info),
]
