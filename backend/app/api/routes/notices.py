from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_visible_notice
from app.core.ratelimit import limit
from app.core.uploads import sniff_mime
from app.db.models import Application, Document, Notice, NoticeLink, User
from app.db.session import get_db
from app.schemas.notice import AskIn, AskOut, NoticeListItem, NoticeOut
from app.services import rag
from app.services.audit import audit
from app.services.eligibility import evaluate
from app.services.guardrails import check_question
from app.services.notice_service import build_notice, file_fingerprint, find_duplicate, link_existing
from app.services.pdf_text import extract_pages
from app.services.profile_store import load_profile
from app.services.readiness import readiness

router = APIRouter(prefix="/notices", tags=["notices"])
MAX_BYTES = 15 * 1024 * 1024


def to_out(n: Notice, shared: bool = False) -> NoticeOut:
    s = n.structured or {}
    return NoticeOut(id=n.id, title=n.title, source_filename=n.source_filename, structured=s,
                     scam_report=n.scam_report, created_at=n.created_at, apply_link=s.get("apply_link"),
                     doc_type=s.get("kind") or s.get("doc_type"), shared=shared, trust=n.trust or "private")


def _mine(db: Session, user: User) -> list[Notice]:
    owned = db.query(Notice).filter(Notice.user_id == user.id).all()
    linked_ids = [r[0] for r in db.query(NoticeLink.notice_id).filter(NoticeLink.user_id == user.id).all()]
    linked = db.query(Notice).filter(Notice.id.in_(linked_ids)).all() if linked_ids else []
    by_id = {n.id: n for n in owned + linked}
    return sorted(by_id.values(), key=lambda n: n.created_at, reverse=True)


@router.post("", response_model=NoticeOut, status_code=201, dependencies=[Depends(limit("ai"))])
async def create_notice(
    file: UploadFile | None = File(None),
    text: str = Form(""),
    title: str = Form(""),
    add_to_tracker: bool = Form(True),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if file is None and not text.strip():
        raise HTTPException(422, "Upload a file or paste the notice text")
    filename, data = "", None
    if file is not None:
        data = await file.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "File is larger than 15 MB")
        filename = file.filename or "notice"
        if sniff_mime(data) is None:
            raise HTTPException(415, "Unsupported or corrupt file. Upload a PDF, image or text file.")
        # Same PDF again? Link to the one shared copy — no re-reading or re-embedding.
        # (Personal-looking files and private notices are never linked; build_notice re-checks.)
        dup = find_duplicate(db, file_fingerprint(data), "")
        if dup is not None and dup.trust != "private":
            notice = link_existing(db, user, dup, add_to_tracker)
            return to_out(notice, shared=notice.user_id != user.id)
        pages = extract_pages(data, filename, file.content_type or "")
    else:
        pages = [p.strip() for p in text.split("\f") if p.strip()]
    if len("\f".join(pages).strip()) < 40:
        raise HTTPException(422, "Could not read enough text from this notice")
    notice = build_notice(db, user, pages, filename, title, add_to_tracker, file_bytes=data)
    return to_out(notice, shared=notice.user_id != user.id)


@router.get("", response_model=list[NoticeListItem])
def list_notices(scam_level: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = _mine(db, user)
    if scam_level:
        rows = [n for n in rows if (n.scam_report or {}).get("level") == scam_level]
    return [NoticeListItem(id=n.id, title=n.title, last_date=(n.structured or {}).get("last_date"),
                           scam_level=(n.scam_report or {}).get("level"), created_at=n.created_at) for n in rows]


@router.get("/{notice_id}", response_model=NoticeOut)
def get_notice(notice_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notice = get_visible_notice(db, notice_id, user)
    return to_out(notice, shared=notice.user_id != user.id)


@router.delete("/{notice_id}", status_code=204)
def delete_notice(notice_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notice = get_visible_notice(db, notice_id, user)
    db.query(Application).filter(Application.user_id == user.id, Application.notice_id == notice.id).update({"notice_id": None})
    if notice.user_id == user.id:
        db.delete(notice)  # owner deleting removes the shared copy for everyone
    else:
        db.query(NoticeLink).filter(NoticeLink.notice_id == notice.id, NoticeLink.user_id == user.id).delete()
    db.commit()


@router.post("/{notice_id}/ask", response_model=AskOut, dependencies=[Depends(limit("ai"))])
def ask(notice_id: int, body: AskIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notice = get_visible_notice(db, notice_id, user)
    verdict = check_question(body.question)
    if not verdict.allowed:
        audit(db, user.id, "guardrail_blocked", reason=verdict.reason, where="notice_ask")
        return AskOut(answer=verdict.message, mode="blocked", citations=[])
    return AskOut(**rag.answer(db, notice, body.question))


@router.get("/{notice_id}/eligibility")
def eligibility(notice_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notice = get_visible_notice(db, notice_id, user)
    return evaluate(notice.structured, load_profile(db, user))


@router.get("/{notice_id}/readiness")
def notice_readiness(notice_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notice = get_visible_notice(db, notice_id, user)
    kinds = {k for (k,) in db.query(Document.kind).filter(Document.user_id == user.id).all()}
    return readiness(notice.structured, kinds)
