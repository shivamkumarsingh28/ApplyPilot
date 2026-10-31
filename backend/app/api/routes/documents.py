from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned
from app.core.uploads import matches_claim
from app.db.models import Document, User
from app.db.session import get_db
from app.schemas.document import DOCUMENT_KINDS, DocumentOut
from app.services.storage import delete_file, load_file, save_file

router = APIRouter(prefix="/documents", tags=["documents"])
MAX_BYTES = 10 * 1024 * 1024
ALLOWED = {"application/pdf", "image/jpeg", "image/png", "image/webp", "text/plain"}


def to_out(d: Document) -> DocumentOut:
    return DocumentOut(id=d.id, kind=d.kind, filename=d.filename, mime=d.mime, size=d.size, created_at=d.created_at,
                       is_original=d.is_original, original_id=d.original_id, application_id=d.application_id,
                       notice_id=d.notice_id, app_ref=d.app_ref or "")


def _quota_check(db: Session, user: User, incoming: int) -> None:
    from app.core.config import get_settings

    s = get_settings()
    if incoming > s.vault_max_file_mb * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {s.vault_max_file_mb} MB")
    total = sum(r[0] for r in db.query(Document.size).filter(Document.user_id == user.id).all()) or 0
    if total + incoming > s.vault_max_total_mb * 1024 * 1024:
        raise HTTPException(413, f"Vault limit of {s.vault_max_total_mb} MB reached. Delete a file first.")


def store_document(db: Session, user: User, data: bytes, filename: str, mime: str, kind: str,
                   is_original: bool = True, original_id: int | None = None,
                   application_id: int | None = None, notice_id: int | None = None, app_ref: str = "") -> Document:
    _quota_check(db, user, len(data))
    doc = Document(user_id=user.id, kind=kind, filename=filename[:255], mime=mime, size=len(data),
                   storage_path=save_file(user.id, data), is_original=is_original, original_id=original_id,
                   application_id=application_id, notice_id=notice_id, app_ref=app_ref)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def app_ref_for(db: Session, user: User, notice_id: int | None) -> tuple[int | None, str]:
    """Find/create the application for a notice and return (application_id, APP-####)."""
    from app.db.models import Application

    if notice_id is None:
        return None, ""
    app_row = db.query(Application).filter(Application.user_id == user.id, Application.notice_id == notice_id).first()
    if app_row is None:
        from app.db.models import Notice

        n = db.get(Notice, notice_id)
        app_row = Application(user_id=user.id, notice_id=notice_id, title=n.title if n else "Application")
        db.add(app_row)
        db.commit()
        db.refresh(app_row)
    return app_row.id, f"APP-{app_row.id:04d}"


@router.post("", response_model=DocumentOut, status_code=201)
async def upload(file: UploadFile = File(...), kind: str = Form("other"), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if kind not in DOCUMENT_KINDS:
        raise HTTPException(422, f"kind must be one of {DOCUMENT_KINDS}")
    if file.content_type not in ALLOWED:
        raise HTTPException(415, "Only PDF, JPEG, PNG, WebP or text files are allowed")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File is larger than 10 MB")
    if not matches_claim(data, file.content_type):
        raise HTTPException(415, "The file content does not match its type")
    return to_out(store_document(db, user, data, file.filename or "upload", file.content_type, kind))


@router.get("", response_model=list[DocumentOut])
def list_documents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Document).filter(Document.user_id == user.id).order_by(Document.created_at.desc()).all()
    return [to_out(d) for d in rows]


@router.get("/{doc_id}/download")
def download(doc_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = get_owned(db, Document, doc_id, user)
    return Response(load_file(doc.storage_path), media_type=doc.mime,
                    headers={"Content-Disposition": f'attachment; filename="{doc.filename}"'})


@router.post("/{doc_id}/copy", response_model=DocumentOut, status_code=201)
def make_copy(doc_id: int, notice_id: int | None = None, application_id: int | None = None,
              user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Application copy of an original (plan 4.4). Original is never modified."""
    doc = get_owned(db, Document, doc_id, user)
    if not doc.is_original:
        raise HTTPException(422, "Only an original can be copied")
    app_id, ref = (application_id, f"APP-{application_id:04d}") if application_id else app_ref_for(db, user, notice_id)
    copy = store_document(db, user, load_file(doc.storage_path), doc.filename, doc.mime, doc.kind,
                          is_original=False, original_id=doc.id, application_id=app_id,
                          notice_id=notice_id, app_ref=ref)
    return to_out(copy)


@router.delete("/{doc_id}", status_code=204)
def remove(doc_id: int, force: bool = False, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = get_owned(db, Document, doc_id, user)
    if doc.is_original:
        copies = db.query(Document).filter(Document.original_id == doc.id).all()
        if copies and not force:
            raise HTTPException(409, "This original has application copies: "
                                + ", ".join(c.app_ref or f"doc {c.id}" for c in copies)
                                + ". Delete with ?force=true to remove them too.")
        for c in copies:
            delete_file(c.storage_path)
            db.delete(c)
    delete_file(doc.storage_path)
    db.delete(doc)
    db.commit()
