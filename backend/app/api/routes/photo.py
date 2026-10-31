import base64

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned
from app.api.routes.documents import store_document
from app.core.ratelimit import limit
from app.core.uploads import sniff_mime
from app.db.models import Notice, User
from app.db.session import get_db
from app.services.photo_studio import process_photo, process_signature

router = APIRouter(prefix="/photo", tags=["photo"])
MAX_BYTES = 12 * 1024 * 1024


@router.post("/process", dependencies=[Depends(limit("ai"))])
async def process(
    file: UploadFile = File(...),
    kind: str = Form("photo"),
    notice_id: int | None = Form(None),
    width: int | None = Form(None),
    height: int | None = Form(None),
    min_kb: int | None = Form(None),
    max_kb: int | None = Form(None),
    format: str | None = Form(None),
    background: str | None = Form(None),
    save_to_vault: bool = Form(False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if kind not in ("photo", "signature"):
        raise HTTPException(422, "kind must be 'photo' or 'signature'")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Image is larger than 12 MB")

    if sniff_mime(data) not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(415, "Please upload a JPG, PNG or WebP image")

    spec: dict = {}
    portal_background = None
    if notice_id is not None:
        notice = get_owned(db, Notice, notice_id, user)
        spec = dict((notice.structured or {}).get("photo_spec" if kind == "photo" else "signature_spec") or {})
        portal_background = spec.get("background")
    from app.services.colours import resolve_background

    if background:
        rgb, label, overridden = resolve_background(background, portal_background)
        spec["background"] = label
        spec["_bg_rgb"] = list(rgb)
        spec["_bg_note"] = (f"The notice requires {portal_background} background, so your choice was not used."
                            if overridden else f"Background: {label}")
    overrides = {"width": width, "height": height, "min_kb": min_kb, "max_kb": max_kb, "format": format}
    spec.update({k: v for k, v in overrides.items() if v not in (None, "")})

    try:
        out, report = (process_photo if kind == "photo" else process_signature)(data, spec)
    except Exception as exc:  # unreadable or corrupt image
        raise HTTPException(422, f"Could not process this image: {exc}") from exc

    if spec.get("_bg_note"):
        report.setdefault("warnings", []).insert(0, spec["_bg_note"])
    fmt = "png" if (spec.get("format") == "png") else "jpg"
    mime = "image/png" if fmt == "png" else "image/jpeg"
    filename = f"{kind}_ready.{fmt}"
    doc_id = None
    app_ref = ""
    if save_to_vault:
        from app.api.routes.documents import app_ref_for

        app_id, app_ref = app_ref_for(db, user, notice_id)
        doc = store_document(db, user, out, filename, mime, kind, is_original=False,
                             application_id=app_id, notice_id=notice_id, app_ref=app_ref)
        doc_id = doc.id
    clean_spec = {k: v for k, v in spec.items() if not k.startswith("_")}
    return {"filename": filename, "mime": mime, "data_base64": base64.b64encode(out).decode(), "report": report,
            "spec": clean_spec, "document_id": doc_id, "app_ref": app_ref}
