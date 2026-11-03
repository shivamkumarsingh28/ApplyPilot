import base64

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_visible_notice
from app.api.routes.documents import store_document
from app.core.ratelimit import limit
from app.core.uploads import sniff_mime
from app.db.models import User
from app.db.session import get_db
from app.services.photo_studio import process_document, process_photo, process_resize, process_signature

router = APIRouter(prefix="/photo", tags=["photo"])
MAX_BYTES = 12 * 1024 * 1024

# mode -> (engine, vault kind). photo_resize is the "only resize, change nothing
# else" mode; document is for certificates/marksheets (no face/background work).
MODES = {
    "photo": (process_photo, "photo"),
    "photo_resize": (process_resize, "photo"),
    "signature": (process_signature, "signature"),
    "document": (process_document, "other"),
}


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
    resize_mode: str | None = Form(None),       # crop | fit | stretch (resize-only/document)
    change_background: bool = Form(True),       # full photo mode: set False to keep the original
    enhance: bool = Form(True),                 # document mode: gentle scan cleanup
    save_to_vault: bool = Form(False),
    save_as: str = Form(""),                    # filename for the vault copy
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if kind not in MODES:
        raise HTTPException(422, "kind must be one of: " + ", ".join(sorted(MODES)))
    if resize_mode and resize_mode not in ("crop", "fit", "stretch"):
        raise HTTPException(422, "resize_mode must be crop, fit or stretch")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Image is larger than 12 MB")

    if sniff_mime(data) not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(415, "Please upload a JPG, PNG or WebP image")

    spec: dict = {}
    portal_background = None
    if notice_id is not None:
        notice = get_visible_notice(db, notice_id, user)
        spec_key = "signature_spec" if kind == "signature" else "photo_spec"
        spec = dict((notice.structured or {}).get(spec_key) or {})
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
    spec["resize_mode"] = resize_mode or "crop"
    spec["change_background"] = change_background
    spec["enhance"] = enhance

    engine, vault_kind = MODES[kind]
    try:
        out, report = engine(data, spec)
    except Exception as exc:  # unreadable or corrupt image
        raise HTTPException(422, f"Could not process this image: {exc}") from exc

    if kind != "photo" or not change_background:
        spec.pop("_bg_note", None)  # background notes only apply when the background is changed
    if spec.get("_bg_note"):
        report.setdefault("warnings", []).insert(0, spec["_bg_note"])
    fmt = "png" if (spec.get("format") == "png") else "jpg"
    mime = "image/png" if fmt == "png" else "image/jpeg"
    filename = (save_as.strip()[:120] or f"{kind}_ready") + f".{fmt}"
    doc_id = None
    app_ref = ""
    if save_to_vault:
        from app.api.routes.documents import app_ref_for

        app_id, app_ref = app_ref_for(db, user, notice_id)
        doc = store_document(db, user, out, filename, mime, vault_kind, is_original=False,
                             application_id=app_id, notice_id=notice_id, app_ref=app_ref)
        doc_id = doc.id
    clean_spec = {k: v for k, v in spec.items() if not k.startswith("_")}
    return {"filename": filename, "mime": mime, "data_base64": base64.b64encode(out).decode(), "report": report,
            "spec": clean_spec, "document_id": doc_id, "app_ref": app_ref}
