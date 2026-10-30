"""Account linking for chat bots.

Flow: the signed-in user asks the web portal for a one-time code (valid 10 min),
sends `/link CODE` to the Telegram bot, the bot calls POST /bot/link with its
shared secret, and receives a token it uses on that user's behalf.
"""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_bot_secret
from app.core.security import create_access_token
from app.db.models import BotLink, User
from app.db.session import get_db
from app.schemas.auth import TokenOut, UserOut

router = APIRouter(prefix="/bot", tags=["bot"])


class LinkIn(BaseModel):
    code: str
    chat_id: str


@router.post("/link-code")
def create_link_code(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    code = secrets.token_hex(4).upper()
    db.add(BotLink(user_id=user.id, code=code, expires_at=datetime.now(UTC) + timedelta(minutes=10)))
    db.commit()
    return {"code": code, "expires_in_minutes": 10}


@router.post("/link", response_model=TokenOut, dependencies=[Depends(require_bot_secret)])
def link(body: LinkIn, db: Session = Depends(get_db)):
    row = db.query(BotLink).filter(BotLink.code == body.code.strip().upper()).first()
    if row is None or row.chat_id is not None:
        raise HTTPException(404, "Code not found or already used")
    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        raise HTTPException(410, "Code expired")
    row.chat_id = body.chat_id
    db.commit()
    user = db.get(User, row.user_id)
    return TokenOut(access_token=create_access_token(user.id, minutes=60 * 24 * 30),
                    user=UserOut(id=user.id, email=user.email, full_name=user.full_name, role=user.role))
