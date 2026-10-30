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


@router.post("/chat", dependencies=[Depends(limit("ai"))])
def chat(body: ChatIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return handle_message(db, user, body.message, body.notice_id)
