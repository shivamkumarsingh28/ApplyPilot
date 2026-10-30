"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import init_db
from app.services.llm.base import LLMError
from app.services.pdf_text import UnreadableDocument


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="ApplyPilot API", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=r"chrome-extension://.*",  # the browser extension calls the API directly
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")  # API responses can hold personal data
        return response

    @app.exception_handler(UnreadableDocument)
    async def _unreadable(_: Request, exc: UnreadableDocument):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(LLMError)
    async def _llm(_: Request, exc: LLMError):
        return JSONResponse(status_code=502, content={"detail": "The AI model is unavailable right now. Try again."})

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
