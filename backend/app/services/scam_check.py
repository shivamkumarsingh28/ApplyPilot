"""Heuristic fake-notice detector.

Each rule adds to a risk score and records a human-readable reason. This is a
screening aid, not proof; the UI says so. Rules target patterns common in
job-scam messages worldwide: payments to personal accounts, guaranteed
selection, urgency, free-mail contacts, and non-official domains on notices that
claim to be from a government body.
"""

from __future__ import annotations

import re

TRUSTED_SUFFIXES = (".gov.in", ".nic.in", ".gov", ".edu", ".ac.in", ".edu.in", ".mil.in", ".gov.uk", ".ac.uk", ".gc.ca")
FREE_MAIL = ("gmail.com", "yahoo.com", "yahoo.in", "hotmail.com", "outlook.com", "rediffmail.com")
GOV_CLAIM = re.compile(r"government|ministry|army|navy|air force|railway|commission|police|recruitment board|defence", re.I)

RULES = [
    (35, r"(?:send|transfer|pay|deposit)[^.\n]{0,60}(?:personal|account|upi|paytm|phonepe|gpay|google pay)|\bupi\b[^.\n]{0,30}(?:id|pay)",
     "Asks you to pay through a personal account or UPI/wallet."),
    (30, r"100\s*%\s*(?:selection|placement|job)|guaranteed (?:job|selection)|direct (?:joining|selection)|without (?:any )?(?:exam|interview)|no exam",
     "Promises a guaranteed job or selection without an exam."),
    (20, r"(?:registration|processing|security|training|kit)\s+(?:fee|deposit|charges?)\b",
     "Charges an unusual fee (registration, security deposit, training kit)."),
    (15, r"limited seats|hurry|last chance|apply immediately|pay immediately|within 24 hours|only \d+ seats",
     "Uses urgency or pressure language."),
    (10, r"whatsapp[^.\n]{0,40}(?:contact|apply|send|number)|(?:contact|apply|send)[^.\n]{0,40}whatsapp",
     "Applications or contact only through WhatsApp."),
]

# Wording that real notices use to warn candidates; it lowers the score.
SAFE_HINTS = re.compile(r"never asks? (?:candidates )?(?:to )?(?:send|pay)|beware of (?:fraud|fake)|only through the official (?:portal|website)", re.I)


def _domains(text: str) -> list[str]:
    found = re.findall(r"(?:https?://)?(?:www\.)?([a-z0-9][a-z0-9\-]*(?:\.[a-z0-9\-]+)+)", text.lower())
    return [d for d in found if not d.endswith((".pdf", ".jpg", ".png", ".doc"))]


def scam_check(text: str) -> dict:
    score = 0
    reasons: list[str] = []
    for weight, pattern, reason in RULES:
        if re.search(pattern, text, re.I):
            score += weight
            reasons.append(reason)

    domains = _domains(text)
    emails = re.findall(r"[\w.+-]+@([\w-]+\.[\w.]+)", text.lower())
    web = [d for d in domains if d not in emails]
    if any(m in emails for m in FREE_MAIL):
        score += 15
        reasons.append("Contact email is a free-mail address, not an official domain.")
    claims_gov = bool(GOV_CLAIM.search(text))
    untrusted = [d for d in web if not d.endswith(TRUSTED_SUFFIXES)]
    trusted = [d for d in web if d.endswith(TRUSTED_SUFFIXES)]
    if claims_gov and untrusted and not trusted:
        score += 25
        reasons.append(f"Claims to be official but links to a non-official domain ({untrusted[0]}).")
    if trusted:
        score -= 10
    if SAFE_HINTS.search(text):
        score -= 10

    score = max(0, min(100, score))
    level = "low" if score < 25 else "medium" if score < 55 else "high"
    return {
        "score": score,
        "level": level,
        "reasons": reasons,
        "domains_seen": sorted(set(web))[:8],
        "tips": ["Apply only through the official website you reach yourself.",
                 "Never pay anyone to 'reserve' a job.",
                 "Check the notice on the organisation's own website."],
        "disclaimer": "Automated screening, not proof. When in doubt, verify with the organisation directly.",
    }
