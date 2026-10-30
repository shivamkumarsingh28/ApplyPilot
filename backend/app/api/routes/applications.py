from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned
from app.db.models import Application, Document, Notice, User
from app.db.session import get_db
from app.schemas.application import ApplicationIn, ApplicationOut, ApplicationPatch

router = APIRouter(prefix="/applications", tags=["applications"])


def to_out(a: Application) -> ApplicationOut:
    left = (a.deadline - date.today()).days if a.deadline else None
    return ApplicationOut(id=a.id, title=a.title, notice_id=a.notice_id, status=a.status, deadline=a.deadline,
                          notes=a.notes, created_at=a.created_at, days_left=left)


@router.get("", response_model=list[ApplicationOut])
def list_applications(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(Application).filter(Application.user_id == user.id).all()
    rows.sort(key=lambda a: (a.deadline is None, a.deadline or date.max))
    return [to_out(a) for a in rows]


@router.get("/summary")
def summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Dashboard numbers: counts by status, next deadline, documents ready, time saved.

    Time saved is a transparent heuristic (notice read 20 min, autofill/tracked
    application 15 min, photo fixed and saved 10 min), not a measurement.
    """
    rows = db.query(Application).filter(Application.user_id == user.id).all()
    open_rows = [a for a in rows if a.status in ("planned", "in_progress")]
    dated = sorted((a for a in open_rows if a.deadline), key=lambda a: a.deadline)
    notices = db.query(Notice).filter(Notice.user_id == user.id).count()
    docs = db.query(Document).filter(Document.user_id == user.id).count()
    nxt = dated[0] if dated else None
    return {
        "total": len(rows),
        "open": len(open_rows),
        "submitted": sum(1 for a in rows if a.status == "submitted"),
        "closed": sum(1 for a in rows if a.status == "closed"),
        "notices": notices,
        "documents_ready": docs,
        "next_deadline": nxt.deadline.isoformat() if nxt else None,
        "next_title": nxt.title if nxt else None,
        "next_days_left": (nxt.deadline - date.today()).days if nxt else None,
        "time_saved_minutes": notices * 20 + len(rows) * 15 + docs * 10,
    }


@router.get("/upcoming", response_model=list[ApplicationOut])
def upcoming(days: int = 7, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Open applications whose deadline falls within `days`. The bot uses this for reminders."""
    limit = date.today() + timedelta(days=days)
    rows = (db.query(Application)
            .filter(Application.user_id == user.id, Application.deadline.isnot(None), Application.deadline <= limit,
                    Application.deadline >= date.today(), Application.status.in_(["planned", "in_progress"]))
            .order_by(Application.deadline).all())
    return [to_out(a) for a in rows]


@router.post("", response_model=ApplicationOut, status_code=201)
def create(body: ApplicationIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    app_row = Application(user_id=user.id, **body.model_dump())
    db.add(app_row)
    db.commit()
    return to_out(app_row)


@router.patch("/{app_id}", response_model=ApplicationOut)
def update(app_id: int, body: ApplicationPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = get_owned(db, Application, app_id, user)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.commit()
    return to_out(row)


@router.delete("/{app_id}", status_code=204)
def delete(app_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = get_owned(db, Application, app_id, user)
    db.delete(row)
    db.commit()
