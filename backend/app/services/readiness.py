"""How ready is this user to apply to a notice?"""

from __future__ import annotations

from datetime import date

LABELS = {
    "photo": "Passport-size photo", "signature": "Signature image", "marksheet_10": "Class 10 certificate",
    "marksheet_12": "Class 12 certificate", "degree": "Degree certificate", "caste_certificate": "Caste/category certificate",
    "domicile": "Domicile certificate", "id_proof": "ID proof", "birth_certificate": "Birth certificate",
}


def readiness(structured: dict, user_doc_kinds: set[str], today: date | None = None) -> dict:
    today = today or date.today()
    required = structured.get("documents") or []
    have = [d for d in required if d in user_doc_kinds]
    missing = [d for d in required if d not in user_doc_kinds]
    pct = 100 if not required else round(100 * len(have) / len(required))
    days_left = None
    if structured.get("last_date"):
        days_left = (date.fromisoformat(structured["last_date"]) - today).days
    return {
        "percent": pct,
        "have": [{"kind": d, "label": LABELS.get(d, d)} for d in have],
        "missing": [{"kind": d, "label": LABELS.get(d, d)} for d in missing],
        "days_left": days_left,
    }
