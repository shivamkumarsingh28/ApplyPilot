"""Guardrails: keep the assistant on its job and keep secrets safe.

Three layers, all deterministic (no model needed, so they cannot be talked out of it):

1. check_question     - runs on every user message BEFORE any model sees it.
2. looks_like_injection - flags uploaded documents that try to give orders to an AI.
3. sanitize_output    - runs on every answer AFTER the model, removing anything that looks like a secret.

These rules are a safety net, not the only protection. The strongest protection is
architectural: tools can only read the signed-in user's own rows (see agents/tools.py).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MAX_QUESTION_CHARS = 500

INJECTION = re.compile(
    r"ignore (?:all |any |the )?(?:previous|prior|above|earlier) (?:instructions|rules|prompts?)|"
    r"disregard (?:all |any |the )?(?:previous|prior|above|your) (?:instructions|rules)|"
    r"(?:reveal|show|print|repeat|tell me) (?:me )?(?:your|the) (?:system |hidden |initial )?(?:prompt|instructions)|"
    r"system prompt|developer mode|jailbreak|\bDAN\b|you are now (?!reading)|pretend (?:to be|you are)|"
    r"act as (?:an? )?(?:unrestricted|different|evil)|new instructions:|override (?:your|the) (?:rules|safety)",
    re.I,
)

DATA_ACCESS = re.compile(
    r"(?:other|another|every|all|someone else'?s?) users?\b|list (?:all )?users|"
    r"(?:show|give|get|dump|export|send)[^.?\n]{0,30}(?:database|all (?:notices|documents|profiles|emails))|"
    r"(?:admin|root) (?:password|token|login)|(?:api|secret|encryption) key|\.env\b|access token|bearer token|"
    r"\bsql\b|drop table|select \* from",
    re.I,
)

UNSAFE = re.compile(
    r"(?:make|build|create|write)[^.?\n]{0,30}(?:bomb|explosive|weapon|malware|ransomware|virus|keylogger)|"
    r"hack (?:into|someone|a )|steal (?:data|passwords|identity)|fake (?:certificate|marksheet|id|documents?)|forge[ds]?\b|"
    r"bypass (?:captcha|security|verification)|crack (?:the )?(?:captcha|password)",
    re.I,
)

SELF_HARM = re.compile(r"\b(?:kill myself|end my life|suicide|self[- ]harm|want to die)\b", re.I)

TOPIC_WORDS = re.compile(
    r"notice|notification|form|appl(?:y|ication)|deadline|last date|closing|fee|age|eligib|document|photo|signature|certificate|"
    r"marksheet|exam|job|post|vacanc|recruit|scholarship|admission|college|university|qualification|category|relax|"
    r"profile|tracker|reminder|safe|scam|fake|genuine|fraud|physical|medical|salary|pay ?scale|syllabus|pattern|"
    r"upload|resize|size|kb|pixel|cut.?off|interview|selection|domicile|caste|height|weight|my notices?|missing|ready|help",
    re.I,
)
GREETING = re.compile(r"^\s*(?:hi|hello|hey|thanks|thank you|namaste|good (?:morning|evening)|ok(?:ay)?)\W*$", re.I)

SECRET_PATTERNS = [
    (re.compile(r"eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}"), "[token removed]"),  # JWT
    (re.compile(r"\b(?:sk|pk|rk)[-_][A-Za-z0-9_\-]{16,}"), "[key removed]"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}"), "Bearer [removed]"),
    (re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*\S{6,}"), r"\1: [removed]"),
    (re.compile(r"\b[A-Fa-f0-9]{40,}\b"), "[hash removed]"),
]


@dataclass
class Verdict:
    allowed: bool
    reason: str | None = None
    message: str = ""


def _block(reason: str, message: str) -> Verdict:
    return Verdict(False, reason, message)


def check_question(text: str, *, strict_topic: bool = False) -> Verdict:
    """Decide whether a user message may reach the assistant."""
    t = (text or "").strip()
    if not t:
        return _block("empty", "Please type a question.")
    if len(t) > MAX_QUESTION_CHARS:
        return _block("too_long", f"Please keep your question under {MAX_QUESTION_CHARS} characters.")
    if SELF_HARM.search(t):
        return _block("self_harm", "I am sorry you are going through this. I cannot help with this topic, but please talk to someone you trust or a local support line right away.")
    if INJECTION.search(t):
        return _block("prompt_injection", "I can only help with your notices, documents and applications. I cannot change my rules.")
    if DATA_ACCESS.search(t):
        return _block("data_access", "I can only show information from your own account.")
    if UNSAFE.search(t):
        return _block("unsafe", "I cannot help with that. I can help you apply honestly with your real documents.")
    if strict_topic and not GREETING.match(t) and not TOPIC_WORDS.search(t):
        return _block("off_topic", "I can help with notices, eligibility, documents, photo and signature rules, and deadlines. Ask me about one of those.")
    return Verdict(True)


def looks_like_injection(document_text: str) -> bool:
    """True when an uploaded document contains text that tries to command an AI."""
    return bool(INJECTION.search(document_text or ""))


def sanitize_output(text: str) -> str:
    out = text or ""
    for pattern, repl in SECRET_PATTERNS:
        out = pattern.sub(repl, out)
    return out
