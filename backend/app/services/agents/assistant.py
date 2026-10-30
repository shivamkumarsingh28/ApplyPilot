"""Orchestrates one assistant turn: guardrails -> supervisor -> agent -> tools -> guardrails."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import User
from app.services.agents import supervisor
from app.services.agents.agents import AGENTS
from app.services.agents.runner import run_agent
from app.services.agents.tools import ToolContext
from app.services.audit import audit
from app.services.guardrails import check_question, sanitize_output


def handle_message(db: Session, user: User, message: str, notice_id: int | None = None) -> dict:
    verdict = check_question(message, strict_topic=True)
    if not verdict.allowed:
        audit(db, user.id, "guardrail_blocked", reason=verdict.reason, where="assistant")
        return {"answer": verdict.message, "agent": None, "route": None, "tools_used": [], "blocked": True, "reason": verdict.reason}

    if len(message.strip()) < 12 and not any(c.isdigit() for c in message) and verdict.allowed and message.strip().lower().rstrip("!. ") in {"hi", "hello", "hey", "thanks", "thank you", "ok", "okay", "namaste"}:
        return {"answer": "Hello! Ask me about your notices, eligibility, documents, photo rules or deadlines.", "agent": None, "route": None, "tools_used": [], "blocked": False, "reason": None}

    decision = supervisor.route(message)
    result = run_agent(AGENTS[decision.agent], message, ToolContext(db=db, user=user, notice_id=notice_id))
    answer = sanitize_output(result.answer)
    audit(db, user.id, "assistant_turn", agent=decision.agent, route=decision.method, tools=[t.tool for t in result.tools_used])
    return {"answer": answer, "agent": decision.agent, "route": {"method": decision.method, "reason": decision.reason},
            "tools_used": [{"tool": t.tool, "ok": t.ok} for t in result.tools_used], "blocked": False, "reason": None}
