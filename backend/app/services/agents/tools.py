"""Tools the agents can call.

SECURITY MODEL: every tool receives a `ToolContext` that already holds the signed-in
user. A tool has no parameter for "which user", so it cannot be asked for someone
else's data, whatever the model (or an attacker's prompt) says. Notice ids are
re-checked against the owner on every call, and a foreign id gets the same
"not found" message as a missing id so nothing leaks.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.db.models import Application, Document, Notice, User
from app.services import rag
from app.services.eligibility import evaluate
from app.services.profile_store import load_profile
from app.services.readiness import readiness
from app.services.scam_check import scam_check  # noqa: F401  (re-exported for tests)

PROFILE_FIELDS = ["full_name", "father_name", "dob", "gender", "category", "qualification", "percentage", "state", "phone", "email"]


class ToolError(Exception):
    """A problem the model can read and explain to the user."""


@dataclass
class ToolContext:
    db: Session
    user: User
    notice_id: int | None = None  # the notice the user has open, if any


@dataclass
class Tool:
    name: str
    description: str
    params: dict[str, str]  # parameter name -> short description
    func: Callable[[ToolContext, dict], dict]
    roles: tuple[str, ...] = ("user", "admin")


def _notice(ctx: ToolContext, args: dict) -> Notice:
    raw = args.get("notice_id", ctx.notice_id)
    if raw in (None, ""):
        mine = ctx.db.query(Notice).filter(Notice.user_id == ctx.user.id).all()
        if len(mine) == 1:
            return mine[0]
        if not mine:
            raise ToolError("You have no notices yet. Add one first.")
        listing = "; ".join(f"#{n.id} {n.title[:40]}" for n in mine[:8])
        raise ToolError(f"Which notice? Open one, or say its number. Yours: {listing}")
    try:
        nid = int(raw)
    except (TypeError, ValueError):
        raise ToolError("notice_id must be a number") from None
    notice = ctx.db.get(Notice, nid)
    if notice is None or notice.user_id != ctx.user.id:
        raise ToolError("Notice not found")
    return notice


def list_notices(ctx: ToolContext, args: dict) -> dict:
    rows = ctx.db.query(Notice).filter(Notice.user_id == ctx.user.id).order_by(Notice.id.desc()).limit(20).all()
    return {"notices": [{"id": n.id, "title": n.title[:80], "last_date": (n.structured or {}).get("last_date"),
                         "safety": (n.scam_report or {}).get("level")} for n in rows]}


def notice_facts(ctx: ToolContext, args: dict) -> dict:
    n = _notice(ctx, args)
    s = n.structured or {}
    return {"notice_id": n.id, "title": n.title, "last_date": s.get("last_date"), "age": s.get("age"),
            "qualification": s.get("qualification"), "fee": s.get("fee"), "documents": s.get("documents"),
            "selection_stages": s.get("selection_stages")}


def ask_notice(ctx: ToolContext, args: dict) -> dict:
    n = _notice(ctx, args)
    question = str(args.get("question") or "").strip()
    if not question:
        raise ToolError("question is required")
    res = rag.answer(ctx.db, n, question)
    return {"notice_id": n.id, "answer": res["answer"], "pages": sorted({c["page"] for c in res["citations"]}), "mode": res["mode"]}


def scam_report(ctx: ToolContext, args: dict) -> dict:
    n = _notice(ctx, args)
    r = n.scam_report or {}
    return {"notice_id": n.id, "level": r.get("level"), "score": r.get("score"), "reasons": r.get("reasons", []), "tips": r.get("tips", [])}


def check_eligibility(ctx: ToolContext, args: dict) -> dict:
    n = _notice(ctx, args)
    res = evaluate(n.structured, load_profile(ctx.db, ctx.user))
    return {"notice_id": n.id, "verdict": res["verdict"], "checks": res["checks"], "missing_profile_fields": res["missing_profile_fields"]}


def check_readiness(ctx: ToolContext, args: dict) -> dict:
    n = _notice(ctx, args)
    kinds = {k for (k,) in ctx.db.query(Document.kind).filter(Document.user_id == ctx.user.id).all()}
    return {"notice_id": n.id, **readiness(n.structured, kinds)}


def profile_gaps(ctx: ToolContext, args: dict) -> dict:
    """Names of missing profile fields only. Values never pass through the model."""
    profile = load_profile(ctx.db, ctx.user)
    return {"missing": [f for f in PROFILE_FIELDS if not profile.get(f)]}


def upcoming_deadlines(ctx: ToolContext, args: dict) -> dict:
    try:
        days = max(1, min(int(args.get("days", 7)), 120))
    except (TypeError, ValueError):
        days = 7
    limit = date.today() + timedelta(days=days)
    rows = (ctx.db.query(Application)
            .filter(Application.user_id == ctx.user.id, Application.deadline.isnot(None), Application.deadline >= date.today(),
                    Application.deadline <= limit, Application.status.in_(["planned", "in_progress"]))
            .order_by(Application.deadline).all())
    return {"days": days, "items": [{"title": a.title[:70], "deadline": a.deadline.isoformat(), "days_left": (a.deadline - date.today()).days} for a in rows]}


def photo_requirements(ctx: ToolContext, args: dict) -> dict:
    n = _notice(ctx, args)
    s = n.structured or {}
    return {"notice_id": n.id, "photo": s.get("photo_spec"), "signature": s.get("signature_spec"),
            "how": "Open Photo studio, choose this notice, upload your picture. It resizes and checks the file for you."}


_TOOLS = [
    Tool("list_notices", "List the user's saved notices.", {}, list_notices),
    Tool("notice_facts", "Key facts of one notice: dates, age, qualification, fee, documents.", {"notice_id": "number, optional"}, notice_facts),
    Tool("ask_notice", "Answer a question using the text of one notice.", {"notice_id": "number, optional", "question": "the question"}, ask_notice),
    Tool("scam_report", "Safety check result of one notice.", {"notice_id": "number, optional"}, scam_report),
    Tool("check_eligibility", "Check the user's profile against one notice's rules.", {"notice_id": "number, optional"}, check_eligibility),
    Tool("check_readiness", "Which required documents the user has or is missing for one notice.", {"notice_id": "number, optional"}, check_readiness),
    Tool("profile_gaps", "Which profile fields the user has not filled yet.", {}, profile_gaps),
    Tool("upcoming_deadlines", "The user's open applications due soon.", {"days": "number, default 7"}, upcoming_deadlines),
    Tool("photo_requirements", "Photo and signature rules of one notice.", {"notice_id": "number, optional"}, photo_requirements),
]
TOOLS: dict[str, Tool] = {t.name: t for t in _TOOLS}


@dataclass
class ToolCallRecord:
    tool: str
    ok: bool
    note: str = ""


def call_tool(name: str, args: dict, ctx: ToolContext, allowed: set[str]) -> tuple[dict, ToolCallRecord]:
    """Run one tool with all checks: known tool, on this agent's allow-list, role permitted."""
    tool = TOOLS.get(name)
    if tool is None or name not in allowed:
        return {"error": "That tool is not available."}, ToolCallRecord(name, False, "not allowed")
    if ctx.user.role not in tool.roles:
        return {"error": "You do not have permission for that."}, ToolCallRecord(name, False, "role")
    safe_args = {k: v for k, v in (args or {}).items() if k in tool.params}  # drop unexpected arguments
    try:
        return tool.func(ctx, safe_args), ToolCallRecord(name, True)
    except ToolError as exc:
        return {"error": str(exc)}, ToolCallRecord(name, False, "tool_error")

