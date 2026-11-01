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


def _visible_notices(ctx: ToolContext) -> list[Notice]:
    from app.db.models import NoticeLink

    owned = ctx.db.query(Notice).filter(Notice.user_id == ctx.user.id).all()
    linked_ids = [r[0] for r in ctx.db.query(NoticeLink.notice_id).filter(NoticeLink.user_id == ctx.user.id).all()]
    linked = ctx.db.query(Notice).filter(Notice.id.in_(linked_ids)).all() if linked_ids else []
    by_id = {n.id: n for n in owned + linked}
    return sorted(by_id.values(), key=lambda n: n.id, reverse=True)


def _notice(ctx: ToolContext, args: dict) -> Notice:
    raw = args.get("notice_id", ctx.notice_id)
    if raw in (None, ""):
        mine = _visible_notices(ctx)
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
    from app.services.notice_service import visible_notice

    notice = visible_notice(ctx.db, nid, ctx.user)
    if notice is None:  # same message for missing and foreign ids: nothing leaks
        raise ToolError("Notice not found")
    return notice


def list_notices(ctx: ToolContext, args: dict) -> dict:
    rows = _visible_notices(ctx)[:20]
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


def _parse_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        raise ToolError(f"{field} must be a date like 2007-03-10") from None


def _num(value, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ToolError(f"{field} must be a number") from None


def calc_age_tool(ctx: ToolContext, args: dict) -> dict:
    from app.services import calculators

    dob_raw = args.get("dob") or load_profile(ctx.db, ctx.user).get("dob")
    if not dob_raw:
        raise ToolError("date of birth is missing: ask the user for it, or add it to the profile")
    as_of = _parse_date(args["as_of"], "as_of") if args.get("as_of") else date.today()
    return calculators.calc_age(_parse_date(dob_raw, "dob"), as_of)


def calc_days_left_tool(ctx: ToolContext, args: dict) -> dict:
    from app.services import calculators

    if args.get("notice_id") or not args.get("target"):
        n = _notice(ctx, args)
        last = (n.structured or {}).get("last_date")
        if not last:
            raise ToolError("no last date found in this notice")
        return calculators.calc_days_left(_parse_date(last, "target"))
    return calculators.calc_days_left(_parse_date(args["target"], "target"))


def calc_age_limit_tool(ctx: ToolContext, args: dict) -> dict:
    from app.services import calculators

    n = _notice(ctx, args)
    age = (n.structured or {}).get("age") or {}
    if age.get("max") is None:
        raise ToolError("no maximum age found in this notice")
    category = args.get("category") or load_profile(ctx.db, ctx.user).get("category") or ""
    return calculators.calc_max_age_with_relaxation(age["max"], age.get("relaxations"), str(category))


def calc_fee_total_tool(ctx: ToolContext, args: dict) -> dict:
    from app.services import calculators

    fees = args.get("fees")
    if not fees:
        n = _notice(ctx, args)
        fee = (n.structured or {}).get("fee") or {}
        if not fee.get("amount"):
            raise ToolError("no fee found in this notice")
        fees = [fee["amount"]]
    return calculators.calc_fee_total([_num(f, "fees") for f in fees])


def calc_percentage_tool(ctx: ToolContext, args: dict) -> dict:
    from app.services import calculators

    if args.get("obtained") in (None, "") or args.get("maximum") in (None, ""):
        raise ToolError("obtained and maximum marks are required")
    try:
        return calculators.calc_percentage(_num(args["obtained"], "obtained"), _num(args["maximum"], "maximum"))
    except ValueError as exc:
        raise ToolError(str(exc)) from None


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
    Tool("calc_age", "Calculate exact age on a date. Use this for any age question; never calculate age yourself.",
         {"dob": "YYYY-MM-DD, optional (default: profile)", "as_of": "YYYY-MM-DD, optional (default: today)"}, calc_age_tool),
    Tool("calc_days_left", "Calculate days left to a notice's last date (or a target date). Use this for deadline questions.",
         {"notice_id": "number, optional", "target": "YYYY-MM-DD, optional"}, calc_days_left_tool),
    Tool("calc_age_limit", "Calculate the maximum age for a category including the notice's relaxation. Use for age-limit questions.",
         {"notice_id": "number, optional", "category": "category, optional (default: profile)"}, calc_age_limit_tool),
    Tool("calc_fee_total", "Add up fees exactly. Use for any fee total question.", {"notice_id": "number, optional", "fees": "list of amounts, optional"}, calc_fee_total_tool),
    Tool("calc_percentage", "Calculate a percentage from obtained and maximum marks.", {"obtained": "number", "maximum": "number"}, calc_percentage_tool),
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

