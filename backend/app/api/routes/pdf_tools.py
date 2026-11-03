"""Small PDF utilities for the website and the chat bots.

Compressing a PDF must never silently turn it into a notice: this route only
shrinks the file (images inside it) and optionally saves the result to the
vault. Reading/RAG ingest stays in /jobs/ingest and only happens on request.
"""

from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.routes.documents import store_document
from app.core.ratelimit import limit
from app.core.uploads import sniff_mime
from app.db.models import User
from app.db.session import get_db
from app.services.pdf_shrink import compress_pdf

router = APIRouter(prefix="/pdf", tags=["pdf"])
MAX_BYTES = 20 * 1024 * 1024


@router.post("/compress", dependencies=[Depends(limit("ai"))])
async def compress(file: UploadFile = File(...), max_kb: int | None = Form(None),
                   save_to_vault: bool = Form(False),
                   user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if max_kb is not None and not (10 <= max_kb <= 10_240):
        raise HTTPException(422, "max_kb must be between 10 and 10240")
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "PDF is larger than 20 MB")
    if sniff_mime(data) != "application/pdf":
        raise HTTPException(415, "Please upload a PDF file")
    try:
        out, info = compress_pdf(data, max_kb)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(422, f"Could not read this PDF: {exc}") from exc
    name = (file.filename or "document.pdf").rsplit(".", 1)[0]
    filename = f"{name}_compressed.pdf"
    doc_id = None
    if save_to_vault:
        doc_id = store_document(db, user, out, filename, "application/pdf", "other", is_original=False).id
    return {"filename": filename, "mime": "application/pdf", "data_base64": base64.b64encode(out).decode(),
            "report": info, "document_id": doc_id}
