"""Audit trail. Records who did what, never the content they handled."""

from sqlalchemy.orm import Session

from app.db.models import AuditLog


def audit(db: Session, user_id: int | None, action: str, **detail) -> None:
    safe = {k: (v[:200] if isinstance(v, str) else v) for k, v in detail.items()}
    db.add(AuditLog(user_id=user_id, action=action, detail=safe))
    db.commit()
