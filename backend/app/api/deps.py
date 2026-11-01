"""Shared FastAPI dependencies: current user, ownership checks, bot secret."""

import hmac

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_db

bearer = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user_id = decode_access_token(creds.credentials)
    user = db.get(User, user_id) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    return user


def require_role(*roles: str):
    """Dependency factory. The role is read from the database on every request, not from the token,
    so removing someone's admin role takes effect immediately."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to do this")
        return user

    return dependency


def get_owned(db: Session, model, obj_id: int, user: User):
    """Fetch a row that must belong to `user`; 404 otherwise (never reveal other users' ids)."""
    obj = db.get(model, obj_id)
    if obj is None or obj.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{model.__name__} not found")
    return obj


def get_visible_notice(db: Session, notice_id: int, user: User):
    """Fetch a notice the user owns OR is linked to (shared library); 404 otherwise."""
    from app.services.notice_service import visible_notice

    notice = visible_notice(db, notice_id, user)
    if notice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notice not found")
    return notice


def require_bot_secret(x_bot_secret: str = Header(default="")) -> None:
    expected = get_settings().bot_shared_secret
    if not expected or not hmac.compare_digest(x_bot_secret, expected):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid bot secret")
