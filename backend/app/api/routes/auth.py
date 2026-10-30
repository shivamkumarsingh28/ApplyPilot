from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.ratelimit import limit
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import Profile, User
from app.db.session import get_db
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut
from app.services.audit import audit

router = APIRouter(prefix="/auth", tags=["auth"])


def _token(user: User) -> TokenOut:
    return TokenOut(access_token=create_access_token(user.id), user=UserOut(id=user.id, email=user.email, full_name=user.full_name, role=user.role))


@router.post("/register", response_model=TokenOut, status_code=201, dependencies=[Depends(limit("login"))])
def register(body: RegisterIn, db: Session = Depends(get_db)):
    email = body.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    role = "admin" if email in get_settings().admin_email_set else "user"
    user = User(email=email, password_hash=hash_password(body.password), full_name=body.full_name, role=role)
    db.add(user)
    db.flush()
    db.add(Profile(user_id=user.id))
    db.commit()
    audit(db, user.id, "register", role=role)
    return _token(user)


@router.post("/login", response_model=TokenOut, dependencies=[Depends(limit("login"))])
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not user.is_active or not verify_password(body.password, user.password_hash):
        audit(db, user.id if user else None, "login_failed", email=body.email.lower())
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")
    audit(db, user.id, "login")
    return _token(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return UserOut(id=user.id, email=user.email, full_name=user.full_name, role=user.role)
