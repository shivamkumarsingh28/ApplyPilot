"""Notice creation shared by web, bot and search ingest.

One public notice is processed exactly once (V2 plan section 10): the file hash
and the cleaned-text hash are fingerprints. A later upload of the same PDF —
by anyone — links to the existing notice instead of re-reading, re-chunking and
re-embedding it. Files that look personal (a marksheet, an ID, a filled form)
are never shared: they stay private to their uploader.
"""
from __future__ import annotations

import hashlib
import re
import time
from datetime import date

from sqlalchemy.orm import Session

from app.db.models import Application, Notice, NoticeLink, User
from app.services import rag
from app.services.extraction import extract_structured
from app.services.guardrails import looks_like_injection
from app.services.scam_check import scam_check

_PERSONAL = re.compile(
    r"marksheet|mark sheet|statement of marks|aadhaar|pan card|passport no|filled (application )?form|"
    r"admit card|hall ticket|score ?card|result card|birth certificate of|certificate of marks", re.I)


def looks_personal(filename: str, text: str) -> bool:
    return bool(_PERSONAL.search(filename or "") or _PERSONAL.search(text[:4000]))


def file_fingerprint(data: bytes | None) -> str:
    return hashlib.sha256(data).hexdigest() if data else ""


def text_fingerprint(pages: list[str]) -> str:
    norm = re.sub(r"\s+", " ", "\f".join(pages).lower()).strip()
    return hashlib.sha256(norm.encode()).hexdigest()


def visible_notice(db: Session, notice_id: int, user: User) -> Notice | None:
    """A notice the user may read: theirs, or one shared with them via a link."""
    notice = db.get(Notice, notice_id)
    if notice is None:
        return None
    if notice.user_id == user.id:
        return notice
    linked = (db.query(NoticeLink)
              .filter(NoticeLink.notice_id == notice_id, NoticeLink.user_id == user.id).first())
    return notice if linked else None


def _tracker_entry(db: Session, user: User, notice: Notice) -> None:
    if db.query(Application).filter(Application.user_id == user.id, Application.notice_id == notice.id).first():
        return
    structured = notice.structured or {}
    deadline = date.fromisoformat(structured["last_date"]) if structured.get("last_date") else None
    db.add(Application(user_id=user.id, notice_id=notice.id, title=notice.title, deadline=deadline))


def link_existing(db: Session, user: User, notice: Notice, add_to_tracker: bool = True) -> Notice:
    """Give `user` instant access to an already-processed notice. No re-ingest.

    A personal-looking notice (marksheet/ID/filled form) is never linked: the
    second uploader simply gets the same private notice back only if it is
    theirs; for anyone else this must not be called (find via build_notice).
    """
    notice.is_shared = True
    if notice.trust == "private":
        notice.trust = "user_shared"
    if notice.user_id != user.id and not db.query(NoticeLink).filter(
            NoticeLink.notice_id == notice.id, NoticeLink.user_id == user.id).first():
        db.add(NoticeLink(user_id=user.id, notice_id=notice.id))
    if add_to_tracker:
        _tracker_entry(db, user, notice)
    db.commit()
    db.refresh(notice)
    return notice


def find_duplicate(db: Session, file_hash: str, text_hash: str) -> Notice | None:
    q = db.query(Notice)
    if file_hash:
        hit = q.filter(Notice.file_hash == file_hash).first()
        if hit:
            return hit
    if text_hash:
        return q.filter(Notice.text_hash == text_hash).first()
    return None


def build_notice(db: Session, user: User, pages: list[str], filename: str, title: str,
                 add_to_tracker: bool = True, timings: dict | None = None,
                 file_bytes: bytes | None = None) -> Notice:
    t = timings if timings is not None else {}
    raw = "\f".join(pages)
    f_hash, t_hash = file_fingerprint(file_bytes), text_fingerprint(pages)
    existing = find_duplicate(db, f_hash, t_hash)
    personal = looks_personal(filename, raw) or (existing is not None and existing.trust == "private")
    if existing is not None and not personal:
        t["deduplicated"] = True
        return link_existing(db, user, existing, add_to_tracker)

    t0 = time.perf_counter()
    structured = extract_structured(raw)
    scam = scam_check(raw)
    if looks_like_injection(raw):
        scam["reasons"].append("The document contains text that tries to give orders to an AI tool.")
        scam["score"] = min(100, scam["score"] + 25)
        scam["level"] = "medium" if scam["score"] < 55 else "high"
    t["extract_s"] = round(time.perf_counter() - t0, 3)
    notice = Notice(user_id=user.id, title=(title.strip() or structured["title"])[:255],
                    source_filename=filename, raw_text=raw, structured=structured, scam_report=scam,
                    file_hash=f_hash, text_hash=t_hash, is_shared=not personal,
                    trust="private" if personal else "user_shared")
    db.add(notice)
    db.flush()
    t0 = time.perf_counter()
    rag.ingest(db, notice, pages)
    t["index_s"] = round(time.perf_counter() - t0, 3)
    if add_to_tracker:
        _tracker_entry(db, user, notice)
    db.commit()
    db.refresh(notice)
    return notice
