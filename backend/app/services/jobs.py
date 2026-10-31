"""DB-backed background ingest (Phase 2 step 1).

Decision (keep-vs-change): a thread worker + job table beats adding Redis/RQ at
current scale — no new infra, works on SQLite, and the sync web path stays for
small pasted text. The plan says move to Redis only when many users arrive.
Status flow: queued -> reading -> indexing -> ready | failed.
"""
from __future__ import annotations

import threading
import time

from sqlalchemy.orm import Session

from app.db.models import IngestJob, User
from app.db.session import get_engine
from app.services.notice_service import build_notice
from app.services.pdf_text import extract_pages


def create_job(db: Session, user_id: int, source: str = "web") -> IngestJob:
    job = IngestJob(user_id=user_id, source=source, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _set(db: Session, job: IngestJob, status: str, **kw) -> None:
    job.status = status
    for k, v in kw.items():
        setattr(job, k, v)
    db.commit()
    db.refresh(job)


def run_job(job_id: int, data: bytes, filename: str, mime: str, title: str = "") -> None:
    """Run in a worker thread. Owns its own DB session."""
    from sqlalchemy.orm import sessionmaker

    db = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)()
    try:
        job = db.get(IngestJob, job_id)
        if job is None:
            return
        user = db.get(User, job.user_id)
        timings: dict = {}
        t0 = time.perf_counter()
        _set(db, job, "reading")
        pages = extract_pages(data, filename, mime) if data else []
        timings["read_s"] = round(time.perf_counter() - t0, 3)
        if len("\f".join(pages).strip()) < 40:
            _set(db, job, "failed", error="Could not read enough text from this notice", timings=timings)
            return
        _set(db, job, "indexing", timings=timings)
        notice = build_notice(db, user, pages, filename, title, timings=timings)
        timings["total_s"] = round(sum(v for v in timings.values() if isinstance(v, (int, float))), 3)
        _set(db, job, "ready", notice_id=notice.id, timings=timings)
    except Exception as exc:  # job must never take the worker down silently
        try:
            job = db.get(IngestJob, job_id)
            if job:
                _set(db, job, "failed", error=str(exc)[:500])
        except Exception:
            db.rollback()
    finally:
        db.close()


def submit(job_id: int, data: bytes, filename: str, mime: str, title: str = "") -> threading.Thread:
    th = threading.Thread(target=run_job, args=(job_id, data, filename, mime, title), daemon=True, name=f"ingest-{job_id}")
    th.start()
    return th
