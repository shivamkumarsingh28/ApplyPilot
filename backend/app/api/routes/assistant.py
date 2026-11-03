from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.ratelimit import limit
from app.db.models import User
from app.db.session import get_db
from app.services.agents.assistant import handle_message

router = APIRouter(prefix="/assistant", tags=["assistant"])


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    notice_id: int | None = None


class FeedbackIn(BaseModel):
    rating: str = Field(pattern="^(up|down)$")
    reason: str = ""


@router.post("/chat", dependencies=[Depends(limit("ai"))])
def chat(body: ChatIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return handle_message(db, user, body.message, body.notice_id)


@router.post("/feedback")
def feedback(body: FeedbackIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Thumbs on an answer (spec 8.4/S10). Stored as an audit event; wrong answers feed the test set."""
    from app.services.audit import audit

    audit(db, user.id, "answer_feedback", rating=body.rating, reason=body.reason[:200], where="web")
    return {"recorded": body.rating}
