"""Database engine and session management."""

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base

_engine = None
_SessionLocal = None


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        url = get_settings().database_url
        connect_args = {}
        if url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
            path = url.replace("sqlite:///", "", 1)
            if path and path != ":memory:":
                os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        _engine = create_engine(url, connect_args=connect_args, future=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def init_db() -> None:
    """Create tables and apply small additive migrations for existing local DBs.

    `create_all` only creates missing tables; it does not add columns to a table
    created by an older version. Phase 2 added vault columns to `documents`, so
    an existing DB otherwise fails at insert time with "no column named ...".
    These ALTERs are idempotent and keep user data intact. Larger production
    deployments should still use Alembic-style migrations.
    """
    from sqlalchemy import text

    from app.db import models  # noqa: F401  (registers models on Base.metadata)

    engine = get_engine()
    Base.metadata.create_all(engine)
    wanted = {
        "documents": {
            "is_original": "BOOLEAN DEFAULT 1",
            "original_id": "INTEGER",
            "application_id": "INTEGER",
            "notice_id": "INTEGER",
            "app_ref": "VARCHAR(20) DEFAULT ''",
        },
    }
    with engine.begin() as conn:
        for table, columns in wanted.items():
            if engine.dialect.name == "sqlite":
                existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))}
            else:
                rows = conn.execute(text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name=:t"), {"t": table})
                existing = {r[0] for r in rows}
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def reset_engine() -> None:
    """Used by tests to point at a fresh database."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None


def get_db() -> Iterator[Session]:
    get_engine()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
