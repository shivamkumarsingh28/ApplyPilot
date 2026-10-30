"""Admin endpoints.

Admins manage accounts and read the audit trail. They can NOT read other users'
profiles, documents or notices: those routes only ever accept the owner's token.
Privacy by design means even a hacked admin account cannot dump user data.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.models import Application, AuditLog, Document, Notice, User
from app.db.session import get_db
from app.services.audit import audit

router = APIRouter(prefix="/admin", tags=["admin"])


class UserPatch(BaseModel):
    role: str | None = None
    is_active: bool | None = None


@router.get("/users")
def list_users(admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    rows = db.query(User).order_by(User.id).all()
    return [{"id": u.id, "email": u.email, "role": u.role, "is_active": u.is_active, "created_at": u.created_at} for u in rows]


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UserPatch, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "User not found")
    if target.id == admin.id:
        raise HTTPException(400, "You cannot change your own role or status")
    if body.role is not None:
        if body.role not in ("user", "admin"):
            raise HTTPException(422, "role must be 'user' or 'admin'")
        target.role = body.role
    if body.is_active is not None:
        target.is_active = body.is_active
    db.commit()
    audit(db, admin.id, "admin_update_user", target=target.id, role=target.role, is_active=target.is_active)
    return {"id": target.id, "role": target.role, "is_active": target.is_active}


@router.get("/audit")
def audit_log(limit: int = 100, admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    rows = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 500)).all()
    return [{"id": r.id, "user_id": r.user_id, "action": r.action, "detail": r.detail, "created_at": r.created_at} for r in rows]


@router.get("/stats")
def stats(admin: User = Depends(require_role("admin")), db: Session = Depends(get_db)):
    count = lambda model: db.query(func.count(model.id)).scalar()  # noqa: E731
    return {"users": count(User), "notices": count(Notice), "documents": count(Document), "applications": count(Application)}
