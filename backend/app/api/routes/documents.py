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
    return DocumentOut(id=d.id, kind=d.kind, filename=d.filename, mime=d.mime, size=d.size, created_at=d.created_at)


def store_document(db: Session, user: User, data: bytes, filename: str, mime: str, kind: str) -> Document:
    doc = Document(user_id=user.id, kind=kind, filename=filename[:255], mime=mime, size=len(data), storage_path=save_file(user.id, data))
    db.add(doc)
    db.commit()
    return doc


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


@router.delete("/{doc_id}", status_code=204)
def remove(doc_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = get_owned(db, Document, doc_id, user)
    delete_file(doc.storage_path)
    db.delete(doc)
    db.commit()
