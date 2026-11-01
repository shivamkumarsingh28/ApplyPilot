from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_visible_notice
from app.db.models import Application, Document, User
from app.db.session import get_db
from app.services.eligibility import evaluate
from app.services.export import checklist_html, ics_calendar
from app.services.profile_store import load_profile
from app.services.readiness import readiness

router = APIRouter(tags=["export"])


@router.get("/notices/{notice_id}/checklist")
def checklist(notice_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notice = get_visible_notice(db, notice_id, user)
    kinds = {k for (k,) in db.query(Document.kind).filter(Document.user_id == user.id).all()}
    profile = load_profile(db, user)
    page = checklist_html(notice.title, notice.structured, evaluate(notice.structured, profile),
                          readiness(notice.structured, kinds), profile)
    return Response(page, media_type="text/html")


@router.get("/applications/calendar.ics")
def calendar(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(Application)
            .filter(Application.user_id == user.id, Application.deadline.isnot(None),
                    Application.status.in_(["planned", "in_progress"]))
            .order_by(Application.deadline).all())
    body = ics_calendar([{"id": a.id, "title": a.title, "deadline": a.deadline.isoformat()} for a in rows])
    return Response(body, media_type="text/calendar",
                    headers={"Content-Disposition": 'attachment; filename="applypilot-deadlines.ics"'})
