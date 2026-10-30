"""Load and save the encrypted profile blob."""

import json

from sqlalchemy.orm import Session

from app.core.crypto import decrypt_text, encrypt_text
from app.db.models import Profile, User
from app.schemas.profile import ProfileData


def load_profile(db: Session, user: User) -> dict:
    prof = db.query(Profile).filter(Profile.user_id == user.id).first()
    data = json.loads(decrypt_text(prof.data_enc)) if prof and prof.data_enc else {}
    data.setdefault("full_name", user.full_name or None)
    data.setdefault("email", user.email)
    return {k: v for k, v in data.items() if v not in (None, "")} | {"ex_servicemen_ward": data.get("ex_servicemen_ward", False)}


def save_profile(db: Session, user: User, data: ProfileData) -> dict:
    payload = data.model_dump(exclude_none=True)
    prof = db.query(Profile).filter(Profile.user_id == user.id).first()
    if prof is None:
        prof = Profile(user_id=user.id)
        db.add(prof)
    prof.data_enc = encrypt_text(json.dumps(payload))
    db.commit()
    return load_profile(db, user)
