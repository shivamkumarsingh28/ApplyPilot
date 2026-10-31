"""OAuth login (plan 3.6): one module, Google first, then GitHub, then LinkedIn.

Implemented with httpx against each provider's standard endpoints instead of a
new dependency — the flow is authorize-URL -> code exchange -> userinfo ->
find-or-create user by verified email -> link row in oauth_accounts.
A provider with no credentials in settings is simply disabled.
LinkedIn note: its OpenID product returns name/email; richer profile fields
need separate product approval, so we never promise them.
"""
from __future__ import annotations

import secrets
from urllib.parse import urlencode

import httpx

from app.core.config import get_settings

PROVIDERS = {
    "google": {"authorize": "https://accounts.google.com/o/oauth2/v2/auth",
               "token": "https://oauth2.googleapis.com/token",
               "userinfo": "https://openidconnect.googleapis.com/v1/userinfo",
               "scope": "openid email profile"},
    "github": {"authorize": "https://github.com/login/oauth/authorize",
               "token": "https://github.com/login/oauth/access_token",
               "userinfo": "https://api.github.com/user",
               "scope": "read:user user:email"},
    "linkedin": {"authorize": "https://www.linkedin.com/oauth/v2/authorization",
                 "token": "https://www.linkedin.com/oauth/v2/accessToken",
                 "userinfo": "https://api.linkedin.com/v2/userinfo",
                 "scope": "openid profile email"},
}


def _creds(provider: str) -> tuple[str, str]:
    s = get_settings()
    return getattr(s, f"{provider}_client_id", ""), getattr(s, f"{provider}_client_secret", "")


def authorize_url(provider: str, state: str) -> str:
    cfg = PROVIDERS[provider]
    cid, _ = _creds(provider)
    s = get_settings()
    q = urlencode({"client_id": cid, "response_type": "code", "scope": cfg["scope"],
                   "redirect_uri": f"{s.oauth_redirect_base}/api/v1/auth/oauth/{provider}/callback", "state": state})
    return f"{cfg['authorize']}?{q}"


def exchange(provider: str, code: str) -> dict:
    """Returns {subject, email, name}. Raises on any provider error."""
    cfg = PROVIDERS[provider]
    cid, secret = _creds(provider)
    s = get_settings()
    r = httpx.post(cfg["token"], data={"client_id": cid, "client_secret": secret, "code": code,
                                       "grant_type": "authorization_code",
                                       "redirect_uri": f"{s.oauth_redirect_base}/api/v1/auth/oauth/{provider}/callback"},
                   headers={"Accept": "application/json"}, timeout=20)
    r.raise_for_status()
    access = r.json()["access_token"]
    u = httpx.get(cfg["userinfo"], headers={"Authorization": "Bearer " + access, "Accept": "application/json"}, timeout=20)
    u.raise_for_status()
    info = u.json()
    email = (info.get("email") or "").lower()
    if provider == "github" and not email:
        e = httpx.get("https://api.github.com/user/emails", headers={"Authorization": "Bearer " + access}, timeout=20)
        if e.is_success:
            email = next((x["email"].lower() for x in e.json() if x.get("primary") and x.get("verified")), "")
    subject = str(info.get("sub") or info.get("id") or "")
    if not subject or not email:
        raise ValueError("Provider did not return a verified email")
    return {"subject": subject, "email": email, "name": info.get("name") or info.get("login") or ""}


def new_state() -> str:
    return secrets.token_urlsafe(24)
