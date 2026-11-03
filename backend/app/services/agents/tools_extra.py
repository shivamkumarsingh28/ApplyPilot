"""Priority tools from the Tool Calling Inventory (groups 1-3, 6-7, 9-10).

Every tool is pure code (no model inside), runs only for the signed-in user
(ToolContext), returns its working, and answers `needs_input` instead of
erroring when something is missing. Registered by tools.py's TOOLS assembly.
"""

from __future__ import annotations

import re
from datetime import date

from app.db.models import Application, Document, Notice
from app.services import rag
from app.services.agents.tools import Tool, ToolContext, ToolError, _notice, _visible_notices, needs_input
from app.services.eligibility import QUAL_ORDER, evaluate
from app.services.extraction import parse_date
from app.services.key_answers import key_answers
from app.services.profile_store import load_profile

# ---------------------------------------------------------------- notice reading

def get_key_answers(ctx: ToolContext, args: dict) -> dict:
    n = _notice(ctx, args)
    return {"notice_id": n.id, "answers": key_answers(n.structured or {})}


def find_in_notice(ctx: ToolContext, args: dict) -> dict:
    n = _notice(ctx, args)
    words = str(args.get("words") or "").strip()
    if not words:
        return needs_input(["words"], {"words": "the words or phrase to search for"})
    hits = rag.retrieve(ctx.db, n.id, words, k=5)
    return {"notice_id": n.id, "matches": [{"page": h["page"], "text": h["text"][:400]} for h in hits]}


def get_notice_page(ctx: ToolContext, args: dict) -> dict:
    n = _notice(ctx, args)
    pages = (n.raw_text or "").split("\f")
    try:
        page = int(args.get("page") or 1)
    except (TypeError, ValueError):
        return needs_input(["page"], {"page": "page number, e.g. 2"})
    if not 1 <= page <= len(pages):
        raise ToolError(f"This notice has {len(pages)} pages; page {page} does not exist")
    return {"notice_id": n.id, "page": page, "of_pages": len(pages), "text": pages[page - 1][:3000]}


def get_ingest_status(ctx: ToolContext, args: dict) -> dict:
    from app.db.models import IngestJob

    jobs = ctx.db.query(IngestJob).filter(IngestJob.user_id == ctx.user.id).order_by(IngestJob.id.desc()).limit(5).all()
    if args.get("job_id"):
        job = next((j for j in jobs if str(j.id) == str(args["job_id"])), None)
        if job is None:
            raise ToolError("Job not found")
        jobs = [job]
    return {"jobs": [{"id": j.id, "status": j.status, "notice_id": j.notice_id, "error": j.error} for j in jobs]}


def explain_eligibility_rule(ctx: ToolContext, args: dict) -> dict:
    n = _notice(ctx, args)
    rule = str(args.get("rule") or "").strip().lower()
    if not rule:
        return needs_input(["rule"], {"rule": "age | qualification | deadline | marks | gender"})
    s = n.structured or {}
    ev = (s.get("evidence") or {}).get(rule)
    detail = {"age": s.get("age"), "qualification": s.get("qualification"), "deadline": s.get("last_date"),
              "marks": (s.get("qualification") or {}).get("min_percentage"), "gender": s.get("gender")}.get(rule)
    if detail in (None, {}, "") and not ev:
        raise ToolError(f"No '{rule}' rule could be read from this notice")
    return {"notice_id": n.id, "rule": rule, "value": detail,
            "exact_text": ev["quote"] if ev else None, "page": ev["page"] if ev else None,
            "note": "Exact text and page from the notice; confirm against the official PDF."}


def check_qualification_tool(ctx: ToolContext, args: dict) -> dict:
    n = _notice(ctx, args)
    required = ((n.structured or {}).get("qualification") or {}).get("level")
    have = args.get("have") or load_profile(ctx.db, ctx.user).get("qualification")
    if not required:
        raise ToolError("No qualification rule could be read from this notice")
    if have not in QUAL_ORDER:
        return needs_input(["have"], {"have": QUAL_ORDER})
    ok = QUAL_ORDER.index(have) >= QUAL_ORDER.index(required)
    return {"notice_id": n.id, "required": required, "you_have": have, "meets": ok,
            "working": f"Required {required}; you have {have}; order is {' < '.join(QUAL_ORDER)}"}


def check_marks_tool(ctx: ToolContext, args: dict) -> dict:
    n = _notice(ctx, args)
    minimum = ((n.structured or {}).get("qualification") or {}).get("min_percentage")
    if minimum in (None, ""):
        raise ToolError("This notice states no minimum percentage")
    pct = args.get("percentage") or load_profile(ctx.db, ctx.user).get("percentage")
    if pct in (None, ""):
        return needs_input(["percentage"])
    try:
        pct = float(pct)
    except (TypeError, ValueError):
        return needs_input(["percentage"])
    return {"notice_id": n.id, "minimum": minimum, "you_have": pct, "meets": pct >= float(minimum),
            "working": f"{pct:g}% vs minimum {float(minimum):g}%"}


def what_if_eligibility(ctx: ToolContext, args: dict) -> dict:
    """Re-run the check with ONE field changed. The saved profile is never touched."""
    n = _notice(ctx, args)
    profile = dict(load_profile(ctx.db, ctx.user))
    change = args.get("change") or {}
    if not isinstance(change, dict) or not change:
        return needs_input(["change"], {"change": "one field, e.g. {\"dob\": \"2006-03-10\"} or {\"category\": \"obc\"}"})
    allowed = {"dob", "category", "qualification", "percentage", "gender"}
    applied = {k: v for k, v in change.items() if k in allowed}
    if not applied:
        return needs_input(["change"], {"change": "one of dob/category/qualification/percentage/gender"})
    profile.update(applied)
    res = evaluate(n.structured, profile)
    return {"notice_id": n.id, "changed": applied, "saved_profile_unchanged": True, **res}


def rank_notices_for_me(ctx: ToolContext, args: dict) -> dict:
    profile = load_profile(ctx.db, ctx.user)
    rows = []
    for n in _visible_notices(ctx):
        res = evaluate(n.structured, profile)
        last = (n.structured or {}).get("last_date")
        days = None
        if last:
            try:
                days = (date.fromisoformat(last) - date.today()).days
            except ValueError:
                days = None
        rows.append({"notice_id": n.id, "title": n.title[:70], "verdict": res["verdict"], "days_left": days})
    order = {"eligible": 0, "needs_info": 1, "not_eligible": 2}
    rows.sort(key=lambda r: (order.get(r["verdict"], 3), r["days_left"] if r["days_left"] is not None else 9999))
    return {"ranked": rows, "how": "Eligible first, then soonest deadline"}


# ---------------------------------------------------------------- profile + chat

def get_profile_summary(ctx: ToolContext, args: dict) -> dict:
    profile = load_profile(ctx.db, ctx.user)
    fields = ["full_name", "dob", "gender", "category", "qualification", "percentage", "state", "phone", "email"]
    filled = [f for f in fields if profile.get(f)]
    return {"filled": filled, "missing": [f for f in fields if not profile.get(f)],
            "extra_fields": [ef.get("label") for ef in profile.get("extra_fields") or []]}


_EDITABLE = {"dob": ("date of birth", lambda v: date.fromisoformat(str(v)[:10]).isoformat()),
             "category": ("category", lambda v: str(v).strip().lower()),
             "qualification": ("qualification", lambda v: str(v).strip().lower()),
             "percentage": ("percentage", lambda v: float(v)),
             "gender": ("gender", lambda v: str(v).strip().lower()),
             "state": ("state", lambda v: str(v).strip()),
             "phone": ("mobile number", lambda v: str(v).strip()),
             "city": ("city", lambda v: str(v).strip())}


def update_profile_field(ctx: ToolContext, args: dict) -> dict:
    """Confirmation arrives here as confirm=true (framework two-step). Validated via ProfileData."""
    field = str(args.get("field") or "").strip()
    if field not in _EDITABLE:
        return needs_input(["field"], {"field": sorted(_EDITABLE)})
    if args.get("value") in (None, ""):
        return needs_input(["value"], {"value": f"your {_EDITABLE[field][0]}"})
    from pydantic import ValidationError

    from app.schemas.profile import ProfileData
    from app.services.profile_store import save_profile

    profile = dict(load_profile(ctx.db, ctx.user))
    try:
        profile[field] = _EDITABLE[field][1](args["value"])
        if field == "qualification" and profile[field] not in QUAL_ORDER:
            raise ToolError("qualification must be one of: " + ", ".join(QUAL_ORDER))
        data = ProfileData(**{k: profile.get(k) for k in ProfileData.model_fields if k in profile} |
                           {"extra_fields": profile.get("extra_fields") or []})
    except (ValueError, ValidationError) as exc:
        raise ToolError(f"That value is not valid for {field}: {exc}") from None
    saved = save_profile(ctx.db, ctx.user, data)
    return {"updated": field, "value": saved.get(field), "profile_saved": True}


def parse_date_text_tool(ctx: ToolContext, args: dict) -> dict:
    text = str(args.get("text") or "").strip()
    if not text:
        return needs_input(["text"], {"text": "a date like 10 March 2007 or 10/3/07"})
    d = parse_date(text)
    if d is None:
        raise ToolError("I could not read a date in that. Try DD Month YYYY, e.g. 10 March 2007")
    return {"iso": d.isoformat(), "working": f"'{text}' -> {d.isoformat()}"}


def validate_contact_fields(ctx: ToolContext, args: dict) -> dict:
    profile = load_profile(ctx.db, ctx.user)
    out = {}
    phone = str(args.get("phone") or profile.get("phone") or "")
    if phone:
        out["phone"] = {"value": phone, "ok": bool(re.fullmatch(r"[+\d][\d\s-]{7,15}", phone))}
    email = str(args.get("email") or profile.get("email") or "")
    if email:
        out["email"] = {"value": email, "ok": bool(re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email))}
    pin = str(args.get("pincode") or profile.get("pincode") or "")
    if pin:
        out["pincode"] = {"value": pin, "ok": bool(re.fullmatch(r"\d{6}", pin))}
    if not out:
        return needs_input(["phone"], {"phone": "fill phone/email/pincode in your profile, or pass one"})
    return out


def record_feedback(ctx: ToolContext, args: dict) -> dict:
    rating = str(args.get("rating") or "").strip().lower()
    if rating not in ("up", "down"):
        return needs_input(["rating"], {"rating": ["up", "down"]})
    from app.services.audit import audit

    audit(ctx.db, ctx.user.id, "answer_feedback", rating=rating, reason=str(args.get("reason") or "")[:200])
    return {"recorded": rating, "thanks": "Feedback saved. Wrong answers are added to the test set."}


def set_active_notice(ctx: ToolContext, args: dict) -> dict:
    n = _notice(ctx, args)
    # Chat state itself is owned by the caller; returning the choice is the contract.
    return {"active_notice_id": n.id, "title": n.title[:80],
            "instruction": f"Use notice_id {n.id} for the next questions about this notice."}


# ---------------------------------------------------------------- vault / tracker

def _doc_row(d: Document) -> dict:
    return {"id": d.id, "kind": d.custom_kind or d.kind, "filename": d.filename, "kb": round((d.size or 0) / 1024, 1),
            "is_original": d.is_original, "app_ref": d.app_ref or "", "notice_id": d.notice_id}


def list_documents(ctx: ToolContext, args: dict) -> dict:
    q = ctx.db.query(Document).filter(Document.user_id == ctx.user.id)
    if args.get("kind"):
        q = q.filter((Document.kind == args["kind"]) | (Document.custom_kind == args["kind"]))
    rows = q.order_by(Document.id.desc()).limit(30).all()
    return {"documents": [_doc_row(d) for d in rows], "count": len(rows)}


def get_storage_usage(ctx: ToolContext, args: dict) -> dict:
    from app.core.config import get_settings

    s = get_settings()
    total = sum(r[0] for r in ctx.db.query(Document.size).filter(Document.user_id == ctx.user.id).all()) or 0
    return {"used_mb": round(total / 1048576, 2), "limit_mb": s.vault_max_total_mb,
            "free_mb": round(max(0, s.vault_max_total_mb * 1048576 - total) / 1048576, 2),
            "files": ctx.db.query(Document).filter(Document.user_id == ctx.user.id).count()}


def list_applications(ctx: ToolContext, args: dict) -> dict:
    q = ctx.db.query(Application).filter(Application.user_id == ctx.user.id)
    if args.get("status"):
        q = q.filter(Application.status == str(args["status"]))
    rows = q.order_by(Application.deadline).limit(30).all()
    return {"applications": [{"id": a.id, "title": a.title[:70], "status": a.status, "notice_id": a.notice_id,
                              "deadline": a.deadline.isoformat() if a.deadline else None} for a in rows]}


def create_application(ctx: ToolContext, args: dict) -> dict:
    n = _notice(ctx, args)
    existing = ctx.db.query(Application).filter(Application.user_id == ctx.user.id, Application.notice_id == n.id).first()
    if existing:
        return {"application_id": existing.id, "already_tracking": True, "title": existing.title[:70]}
    deadline = None
    if (n.structured or {}).get("last_date"):
        try:
            deadline = date.fromisoformat(n.structured["last_date"])
        except ValueError:
            deadline = None
    app_row = Application(user_id=ctx.user.id, notice_id=n.id, title=n.title[:255], deadline=deadline)
    ctx.db.add(app_row)
    ctx.db.commit()
    return {"application_id": app_row.id, "title": app_row.title[:70], "deadline": deadline.isoformat() if deadline else None}


def update_application_status(ctx: ToolContext, args: dict) -> dict:
    status = str(args.get("status") or "").strip()
    if status not in ("planned", "in_progress", "submitted", "closed"):
        return needs_input(["status"], {"status": ["planned", "in_progress", "submitted", "closed"]})
    try:
        app_id = int(args.get("application_id"))
    except (TypeError, ValueError):
        return needs_input(["application_id"])
    app_row = ctx.db.get(Application, app_id)
    if app_row is None or app_row.user_id != ctx.user.id:
        raise ToolError("Application not found")
    app_row.status = status
    ctx.db.commit()
    return {"application_id": app_row.id, "status": status}


def get_application_checklist(ctx: ToolContext, args: dict) -> dict:
    try:
        app_id = int(args.get("application_id"))
    except (TypeError, ValueError):
        return needs_input(["application_id"])
    app_row = ctx.db.get(Application, app_id)
    if app_row is None or app_row.user_id != ctx.user.id:
        raise ToolError("Application not found")
    steps = [{"step": "Notice saved", "done": app_row.notice_id is not None}]
    if app_row.notice_id:
        kinds = {k for (k,) in ctx.db.query(Document.kind).filter(Document.user_id == ctx.user.id).all()}
        notice = ctx.db.get(Notice, app_row.notice_id)
        if notice is not None:
            from app.services.readiness import readiness

            r = readiness(notice.structured, kinds)
            steps.append({"step": f"Documents ready ({r['percent']}%)", "done": r["percent"] == 100})
    steps.append({"step": "Marked submitted", "done": app_row.status in ("submitted", "closed")})
    return {"application_id": app_id, "title": app_row.title[:70], "status": app_row.status, "steps": steps}


def find_duplicate_documents(ctx: ToolContext, args: dict) -> dict:
    rows = ctx.db.query(Document).filter(Document.user_id == ctx.user.id).all()
    seen: dict[tuple, list] = {}
    for d in rows:
        seen.setdefault((d.filename, d.size), []).append(d.id)
    dups = [{"filename": k[0], "kb": round(k[1] / 1024, 1), "ids": v} for k, v in seen.items() if len(v) > 1]
    return {"duplicates": dups, "note": "Same name and size. Originals are never deleted automatically."}


# ---------------------------------------------------------------- discover

_OFFICIAL_SUFFIXES = (".gov.in", ".nic.in", ".gov", ".ac.in", ".edu", ".org.in", ".co.in")


def check_url_trust(ctx: ToolContext, args: dict) -> dict:
    url = str(args.get("url") or "").strip()
    if not url:
        return needs_input(["url"])
    host = re.sub(r"^https?://", "", url).split("/")[0].lower()
    official = any(host.endswith(s) or host == s.lstrip(".") for s in _OFFICIAL_SUFFIXES)
    return {"host": host, "looks_official": official,
            "note": "Official-looking domain. Still verify on the organisation's own site." if official
                    else "Not a known official domain pattern. Be careful: check the link inside the official notice."}


def find_in_library(ctx: ToolContext, args: dict) -> dict:
    title = str(args.get("title") or "").strip().lower()
    rows = ctx.db.query(Notice).filter(Notice.is_shared.is_(True)).order_by(Notice.id.desc()).limit(50).all()
    if title:
        rows = [n for n in rows if title in (n.title or "").lower()]
    return {"library": [{"notice_id": n.id, "title": n.title[:70], "trust": n.trust,
                         "yours": n.user_id == ctx.user.id} for n in rows[:10]]}


def link_library_notice(ctx: ToolContext, args: dict) -> dict:
    from app.services.notice_service import link_existing

    try:
        nid = int(args.get("notice_id"))
    except (TypeError, ValueError):
        return needs_input(["notice_id"])
    notice = ctx.db.get(Notice, nid)
    if notice is None or not notice.is_shared or notice.trust == "private":
        raise ToolError("That notice is not in the shared library")
    linked = link_existing(ctx.db, ctx.user, notice)
    return {"linked_notice_id": linked.id, "title": linked.title[:70], "instant": True}


def is_public_notice_tool(ctx: ToolContext, args: dict) -> dict:
    from app.services.notice_service import looks_personal

    n = _notice(ctx, args)
    personal = looks_personal(n.source_filename or "", (n.raw_text or "")[:4000])
    return {"notice_id": n.id, "looks_personal": personal,
            "shareable": not personal and (n.scam_report or {}).get("level") != "high",
            "note": "Personal files never enter the shared library." if personal else "Public-looking notice; safety level travels with it."}


def convert_grade_tool(ctx: ToolContext, args: dict) -> dict:
    try:
        cgpa = float(args.get("cgpa"))
        mult = float(args.get("multiplier") or 9.5)
    except (TypeError, ValueError):
        return needs_input(["cgpa"], {"cgpa": "e.g. 8.2", "multiplier": "from the notice, default 9.5"})
    pct = round(cgpa * mult, 2)
    return {"cgpa": cgpa, "multiplier": mult, "percentage": pct,
            "working": f"{cgpa:g} x {mult:g} = {pct:g}% (use the notice's own formula when it states one)"}


EXTRA_TOOLS: list[Tool] = [
    Tool("get_key_answers", "The quick answers made when the notice was read (fee, last date, age, documents). Use for a fast summary.",
         {"notice_id": "number, optional"}, get_key_answers),
    Tool("find_in_notice", "Find passages in the notice matching words, with pages. Use when the user asks where something is written.",
         {"notice_id": "number, optional", "words": "words or phrase"}, find_in_notice),
    Tool("get_notice_page", "Read one full page of the notice text.", {"notice_id": "number, optional", "page": "page number"}, get_notice_page),
    Tool("get_ingest_status", "Status of notice-reading jobs (queued/reading/ready/failed).", {"job_id": "number, optional"}, get_ingest_status),
    Tool("explain_eligibility_rule", "Show one eligibility rule with its exact sentence and page from the notice.",
         {"notice_id": "number, optional", "rule": "age|qualification|deadline|marks|gender"}, explain_eligibility_rule),
    Tool("check_qualification", "Compare the user's qualification level with what the notice requires.",
         {"notice_id": "number, optional", "have": "level, optional (default: profile)"}, check_qualification_tool, kind="compute"),
    Tool("check_marks", "Compare the user's percentage with the notice's minimum percentage.",
         {"notice_id": "number, optional", "percentage": "number, optional (default: profile)"}, check_marks_tool, kind="compute"),
    Tool("what_if_eligibility", "Eligibility with ONE changed input (e.g. a different category), without saving anything.",
         {"notice_id": "number, optional", "change": "object, e.g. {\"category\": \"obc\"}"}, what_if_eligibility, kind="compute"),
    Tool("rank_notices_for_me", "Rank the user's notices: eligible first, then soonest deadline.", {}, rank_notices_for_me, kind="compute"),
    Tool("get_profile_summary", "Which profile fields are filled and which are missing (names only, never values).", {}, get_profile_summary),
    Tool("update_profile_field", "Save ONE profile field (date of birth, category, qualification, percentage, gender, state, phone, city). Always confirm first.",
         {"field": "field name", "value": "new value"}, update_profile_field, kind="write", confirm=True),
    Tool("parse_date_text", "Turn date words like '10 March 2007' or '10/3/07' into an exact date.", {"text": "date words"}, parse_date_text_tool, kind="compute"),
    Tool("validate_contact_fields", "Check phone, email and PIN code formats.", {"phone": "optional", "email": "optional", "pincode": "optional"}, validate_contact_fields, kind="compute"),
    Tool("record_feedback", "Record that the last answer was right (up) or wrong (down), with a reason.",
         {"rating": "up|down", "reason": "optional"}, record_feedback, kind="write"),
    Tool("set_active_notice", "Make one notice the one this chat is about.", {"notice_id": "number, optional"}, set_active_notice, kind="write"),
    Tool("list_documents", "List the user's vault files, optionally by kind.", {"kind": "optional"}, list_documents),
    Tool("get_storage_usage", "Vault space used and free.", {}, get_storage_usage),
    Tool("list_applications", "List tracked applications, optionally by status.", {"status": "optional"}, list_applications),
    Tool("create_application", "Start tracking a notice as an application.", {"notice_id": "number, optional"}, create_application, kind="write", confirm=True),
    Tool("update_application_status", "Change an application's status (planned, in_progress, submitted, closed).",
         {"application_id": "number", "status": "planned|in_progress|submitted|closed"}, update_application_status, kind="write", confirm=True),
    Tool("get_application_checklist", "Steps done and remaining for one application.", {"application_id": "number"}, get_application_checklist, kind="compute"),
    Tool("find_duplicate_documents", "Spot likely duplicate files in the vault (same name and size).", {}, find_duplicate_documents),
    Tool("check_url_trust", "Whether a link looks like an official domain.", {"url": "link"}, check_url_trust, kind="compute"),
    Tool("find_in_library", "Search the shared notice library by title.", {"title": "optional words"}, find_in_library),
    Tool("link_library_notice", "Add a shared-library notice to the user's list instantly.", {"notice_id": "number"}, link_library_notice, kind="write", confirm=True),
    Tool("is_public_notice", "Check a notice looks public (shareable) and not personal.", {"notice_id": "number, optional"}, is_public_notice_tool),
    Tool("convert_grade", "Convert CGPA to percentage with a multiplier.", {"cgpa": "number", "multiplier": "number, default 9.5"}, convert_grade_tool, kind="compute"),
]
