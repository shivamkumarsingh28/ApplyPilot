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


# Shared chat helpers (Inventory group 10) are available to every agent, on top
# of its own allow-list. Each agent still sees a SHORT list (~8 own + 3 shared):
# a model chooses better from a short list.
SHARED_TOOLS: tuple[str, ...] = ("record_feedback", "set_active_notice", "get_profile_summary")

AGENTS: dict[str, Agent] = {a.name: a for a in [
    Agent("notice_agent", "Answers questions about the content of a notice: dates, fees, exam stages, rules, safety, key answers, finding passages.",
          ("list_notices", "notice_facts", "ask_notice", "scam_report", "get_key_answers", "find_in_notice", "get_notice_page", "get_ingest_status") + SHARED_TOOLS,
          ("notice", "fee", "last date", "exam", "stage", "physical", "medical", "syllabus", "safe", "scam", "fake", "fraud", "genuine", "summary", "tell me about", "vacanc", "salary", "organisation", "organization", "who issued", "page")),
    Agent("eligibility_agent", "Checks if the user can apply, calculates age/fees/marks, and explains the exact rule with its page.",
          ("check_eligibility", "explain_eligibility_rule", "check_qualification", "check_marks", "what_if_eligibility",
           "calc_age", "calc_age_limit", "check_readiness", "profile_gaps") + SHARED_TOOLS,
          ("eligible", "eligibility", "can i apply", "am i", "age", "qualify", "qualification", "ready", "missing", "documents do i", "documents are missing", "documents missing", "relaxation", "profile", "days left", "percentage", "%", "marks", "what if", "cgpa")),
    Agent("tracker_agent", "Deadlines, applications the user is tracking, ranking notices, and checklists.",
          ("upcoming_deadlines", "list_applications", "create_application", "update_application_status", "get_application_checklist",
           "rank_notices_for_me", "calc_days_left", "list_notices") + SHARED_TOOLS,
          ("deadline", "due", "reminder", "this week", "next week", "upcoming", "closing soon", "my applications", "apply first", "which notice should", "tracker", "submitted", "rank", "best for me", "checklist")),
    Agent("photo_agent", "Photo and signature studio: requirements, quality checks, face, colour, and one-step preparation to a notice's rules.",
          ("photo_requirements", "get_image_requirements", "inspect_image", "detect_face", "check_photo_quality",
           "parse_color_name", "prepare_for_notice", "list_documents") + SHARED_TOOLS,
          ("photo", "signature", "picture", "resize", "pixel", "kb", "image size", "passport size", "background", "colour", "color", "blur", "quality")),
    Agent("profile_agent", "The user's profile: what is filled, what is missing, saving one field, contact checks, date reading.",
          ("get_profile_summary", "profile_gaps", "update_profile_field", "parse_date_text", "validate_contact_fields", "check_eligibility") + SHARED_TOOLS,
          ("profile", "my details", "date of birth", "dob", "phone", "email", "pin code", "update", "change my", "save my")),
    Agent("documents_agent", "The vault: listing files, copies for applications, storage, duplicate and document information.",
          ("list_documents", "get_storage_usage", "make_application_copy", "list_application_documents", "get_document_info",
           "find_duplicate_documents", "check_readiness") + SHARED_TOOLS,
          ("vault files", "my vault", "vault document", "copy of", "storage", "duplicate file", "certificate file", "marksheet file")),
    Agent("discover_agent", "Finding notices: shared library, official-link checks, and whether a notice is public.",
          ("find_in_library", "link_library_notice", "check_url_trust", "is_public_notice", "list_notices", "get_key_answers") + SHARED_TOOLS,
          ("library", "shared", "official", "website", "link", "trust", "already uploaded", "same notice", "find notice", "search")),
]}
DEFAULT_AGENT = "notice_agent"
