"""Pre-computed key answers shown when ingest finishes (plan 4.1/3.3)."""
from __future__ import annotations


def key_answers(structured: dict) -> list[str]:
    s = structured or {}
    lines = []
    if s.get("last_date"):
        lines.append(f"Last date: {s['last_date']}")
    age = s.get("age") or {}
    if age.get("min") is not None or age.get("max") is not None:
        lines.append(f"Age: {age.get('min')}–{age.get('max')} years" + (f" (as on {age['as_of']})" if age.get("as_of") else ""))
    fee = s.get("fee") or {}
    if fee.get("amount"):
        lines.append(f"Fee: {fee.get('currency', 'INR')} {fee['amount']}")
    if s.get("start_date"):
        lines.append(f"Start date: {s['start_date']}")
    if s.get("vacancies"):
        lines.append(f"Vacancies: {s['vacancies']}")
    if (s.get("salary") or {}).get("amount"):
        lines.append(f"Salary: {s['salary'].get('currency', 'INR')} {s['salary']['amount']}")
    if s.get("apply_link"):
        lines.append(f"Apply here: {s['apply_link']}")
    qual = (s.get("qualification") or {}).get("level")
    if qual:
        lines.append(f"Qualification: {qual}")
    if s.get("documents"):
        lines.append("Documents: " + ", ".join(str(d).replace("_", " ") for d in s["documents"]))
    return lines
