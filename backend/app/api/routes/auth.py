from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.ratelimit import limit
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import OAuthAccount, Profile, User
from app.db.session import get_db
from app.schemas.auth import LoginIn, RegisterIn, TokenOut, UserOut
from app.services import oauth as oauth_svc
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


@router.get("/providers")
def providers():
    return {"providers": get_settings().oauth_providers, "email_password": True}


@router.get("/oauth/{provider}/start")
def oauth_start(provider: str, request: Request):
    if provider not in get_settings().oauth_providers:
        raise HTTPException(404, "That login provider is not enabled")
    state = oauth_svc.new_state()
    resp = RedirectResponse(oauth_svc.authorize_url(provider, state))
    resp.set_cookie("oauth_state", state, httponly=True, max_age=600, samesite="lax")
    return resp


@router.get("/oauth/{provider}/callback")
def oauth_callback(provider: str, code: str, state: str, request: Request, db: Session = Depends(get_db)):
    if provider not in get_settings().oauth_providers:
        raise HTTPException(404, "That login provider is not enabled")
    if not state or state != request.cookies.get("oauth_state"):
        raise HTTPException(400, "Login state mismatch. Please try again.")
    try:
        info = oauth_svc.exchange(provider, code)
    except Exception:
        raise HTTPException(502, "The login provider could not be reached") from None
    link = db.query(OAuthAccount).filter(OAuthAccount.provider == provider,
                                         OAuthAccount.provider_subject == info["subject"]).first()
    if link:
        user = db.get(User, link.user_id)
    else:
        user = db.query(User).filter(User.email == info["email"]).first()
        if user is None:
            user = User(email=info["email"], password_hash=hash_password(oauth_svc.new_state()),
                        full_name=info["name"], role="admin" if info["email"] in get_settings().admin_email_set else "user")
            db.add(user)
            db.flush()
            db.add(Profile(user_id=user.id))
        db.add(OAuthAccount(user_id=user.id, provider=provider, provider_subject=info["subject"], email=info["email"]))
    db.commit()
    audit(db, user.id, "oauth_login", provider=provider)
    token = create_access_token(user.id)
    # One-time handoff: the page stores the token then clears it from the URL bar.
    return HTMLResponse(f"<script>localStorage.setItem('applypilot_token',{token!r});location.href='/';</script>")


@router.get("/linked")
def linked(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(OAuthAccount).filter(OAuthAccount.user_id == user.id).all()
    return [{"provider": r.provider, "email": r.email} for r in rows]
