from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned
from app.core.uploads import sniff_mime
from app.db.models import IngestJob, Notice, User
from app.db.session import get_db
from app.services import jobs as jobsvc
from app.services.key_answers import key_answers

router = APIRouter(prefix="/jobs", tags=["jobs"])
MAX_BYTES = 5 * 1024 * 1024


def _out(j: IngestJob, db: Session) -> dict:
    out = {"id": j.id, "status": j.status, "notice_id": j.notice_id, "error": j.error,
           "source": j.source, "timings": j.timings or {}, "summary": [], "title": None}
    if j.notice_id:
        n = db.get(Notice, j.notice_id)
        if n:
            out["title"] = n.title
            out["summary"] = key_answers(n.structured)
    return out


@router.post("/ingest", status_code=202)
async def ingest_async(file: UploadFile = File(...), title: str = Form(""), source: str = Form("web"),
                         user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File is larger than 5 MB")
    if sniff_mime(data) is None:
        raise HTTPException(415, "Unsupported or corrupt file. Upload a PDF, image or text file.")
    job = jobsvc.create_job(db, user.id, source if source in ("web", "bot", "search") else "web")
    jobsvc.submit(job.id, data, file.filename or "notice", file.content_type or "")
    return {"job_id": job.id, "status": "queued", "message": "Got it, reading your notice. I will tell you when it is ready."}


@router.get("/{job_id}")
def get_job(job_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _out(get_owned(db, IngestJob, job_id, user), db)
