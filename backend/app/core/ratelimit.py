"""Small in-memory sliding-window rate limiter.

Good enough for one server process. With several replicas, move the counters to
Redis (see docs/SECURITY.md). Limits slow down password guessing and protect the
model quota from a single noisy client.
"""

import hashlib
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

from app.core.config import get_settings

_hits: dict[str, deque] = defaultdict(deque)


def reset() -> None:
    _hits.clear()


def _key(request: Request, bucket: str) -> str:
    auth = request.headers.get("authorization", "")
    who = hashlib.sha256(auth.encode()).hexdigest()[:16] if auth else (request.client.host if request.client else "unknown")
    return f"{bucket}:{who}"


def limit(bucket: str):
    """FastAPI dependency factory. bucket is one of: login, ai, general."""

    def dependency(request: Request) -> None:
        s = get_settings()
        per_minute = {"login": s.login_rate_limit_per_minute, "ai": s.ai_rate_limit_per_minute}.get(bucket, s.rate_limit_per_minute)
        if bucket == "login":  # key by IP only: the attacker controls the other headers
            key = f"login:{request.client.host if request.client else 'unknown'}"
        else:
            key = _key(request, bucket)
        now = time.monotonic()
        window = _hits[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= per_minute:
            raise HTTPException(429, "Too many requests. Please wait a minute and try again.",
                                headers={"Retry-After": "60"})
        window.append(now)

    return dependency
