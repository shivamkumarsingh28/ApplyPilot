from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.profile import ProfileData
from app.services.profile_store import load_profile, save_profile

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return load_profile(db, user)


@router.put("")
def put_profile(body: ProfileData, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return save_profile(db, user, body)
