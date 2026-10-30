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
    if notice_id is not None:
        notice = get_owned(db, Notice, notice_id, user)
        spec = dict((notice.structured or {}).get("photo_spec" if kind == "photo" else "signature_spec") or {})
    overrides = {"width": width, "height": height, "min_kb": min_kb, "max_kb": max_kb, "format": format, "background": background}
    spec.update({k: v for k, v in overrides.items() if v not in (None, "")})

    try:
        out, report = (process_photo if kind == "photo" else process_signature)(data, spec)
    except Exception as exc:  # unreadable or corrupt image
        raise HTTPException(422, f"Could not process this image: {exc}") from exc

    fmt = "png" if (spec.get("format") == "png") else "jpg"
    mime = "image/png" if fmt == "png" else "image/jpeg"
    filename = f"{kind}_ready.{fmt}"
    doc_id = None
    if save_to_vault:
        doc_id = store_document(db, user, out, filename, mime, kind).id
    return {"filename": filename, "mime": mime, "data_base64": base64.b64encode(out).decode(), "report": report,
            "spec": spec, "document_id": doc_id}
