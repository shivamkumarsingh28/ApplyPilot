"""Notice creation shared by web, bot and search ingest.

Extracted from routes/notices.py so the synchronous web path and the background
job run exactly the same pipeline (and timings are comparable).
"""
from __future__ import annotations

import time
from datetime import date

from sqlalchemy.orm import Session

from app.db.models import Application, Notice, User
from app.services import rag
from app.services.extraction import extract_structured
from app.services.guardrails import looks_like_injection
from app.services.scam_check import scam_check


def build_notice(db: Session, user: User, pages: list[str], filename: str, title: str,
                 add_to_tracker: bool = True, timings: dict | None = None) -> Notice:
    t = timings if timings is not None else {}
    t0 = time.perf_counter()
    raw = "\f".join(pages)
    structured = extract_structured(raw)
    scam = scam_check(raw)
    if looks_like_injection(raw):
        scam["reasons"].append("The document contains text that tries to give orders to an AI tool.")
        scam["score"] = min(100, scam["score"] + 25)
        scam["level"] = "medium" if scam["score"] < 55 else "high"
    t["extract_s"] = round(time.perf_counter() - t0, 3)
    notice = Notice(user_id=user.id, title=(title.strip() or structured["title"])[:255],
                    source_filename=filename, raw_text=raw, structured=structured, scam_report=scam)
    db.add(notice)
    db.flush()
    t0 = time.perf_counter()
    rag.ingest(db, notice, pages)
    t["index_s"] = round(time.perf_counter() - t0, 3)
    if add_to_tracker:
        deadline = date.fromisoformat(structured["last_date"]) if structured.get("last_date") else None
        db.add(Application(user_id=user.id, notice_id=notice.id, title=notice.title, deadline=deadline))
    db.commit()
    db.refresh(notice)
    return notice
