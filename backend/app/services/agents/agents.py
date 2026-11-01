"""The specialist agents.

Each agent owns a small allow-list of tools. The supervisor picks the agent; the
agent picks the tool. An agent can never call a tool outside its own list.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Agent:
    name: str
    description: str  # shown to the supervisor model when it chooses
    tools: tuple[str, ...]
    keywords: tuple[str, ...]  # used for routing when no model is available


AGENTS: dict[str, Agent] = {a.name: a for a in [
    Agent("notice_agent", "Answers questions about the content of a notice: dates, fees, exam stages, rules, safety.",
          ("list_notices", "notice_facts", "ask_notice", "scam_report"),
          ("notice", "fee", "last date", "exam", "stage", "physical", "medical", "syllabus", "safe", "scam", "fake", "fraud", "genuine", "summary", "tell me about", "vacanc", "salary")),
    Agent("eligibility_agent", "Checks if the user can apply and what documents or profile details are missing.",
          ("check_eligibility", "check_readiness", "profile_gaps", "notice_facts",
           "calc_age", "calc_days_left", "calc_age_limit", "calc_fee_total", "calc_percentage"),
          ("eligible", "eligibility", "can i apply", "am i", "age", "qualify", "qualification", "ready", "missing", "documents do i", "relaxation", "profile", "days left", "percentage", "%", "marks")),
    Agent("tracker_agent", "Shows deadlines and the user's open applications.",
          ("upcoming_deadlines", "list_notices"),
          ("deadline", "due", "reminder", "this week", "next week", "upcoming", "closing soon", "my applications", "tracker")),
    Agent("photo_agent", "Explains photo and signature requirements and how to prepare them.",
          ("photo_requirements", "notice_facts"),
          ("photo", "signature", "picture", "resize", "pixel", "kb", "image size", "passport size")),
]}
DEFAULT_AGENT = "notice_agent"
