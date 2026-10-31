from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.ratelimit import limit
from app.db.models import User
from app.db.session import get_db
from app.services import jobs as jobsvc
from app.services.web_search import SearchUnavailable, fetch_page, search

router = APIRouter(prefix="/search", tags=["search"])


class SaveIn(BaseModel):
    url: str = Field(max_length=2000)


@router.get("", dependencies=[Depends(limit("ai"))])
def do_search(q: str, user: User = Depends(get_current_user)):
    if len(q.strip()) < 3:
        raise HTTPException(422, "Search needs at least 3 characters")
    try:
        return {"results": search(q.strip())}
    except SearchUnavailable as exc:
        raise HTTPException(503, str(exc)) from None


@router.post("/save", status_code=202, dependencies=[Depends(limit("ai"))])
def save_as_notice(body: SaveIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        data, mime = fetch_page(body.url)
    except SearchUnavailable as exc:
        raise HTTPException(422, str(exc)) from None
    job = jobsvc.create_job(db, user.id, "search")
    jobsvc.submit(job.id, data, body.url.rsplit("/", 1)[-1] or "notice", mime)
    return {"job_id": job.id, "status": "queued"}
