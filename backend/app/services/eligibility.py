"""Deterministic eligibility engine.

Eligibility is arithmetic and rules, so it is NOT delegated to a language model.
The model extracts the rules from the notice (services/extraction.py); this module
applies them to the user's profile and explains every verdict check by check.
"""

from __future__ import annotations

from datetime import date

from app.services.extraction import QUAL_ORDER

QUAL_LABEL = {
    "below_10th": "below 10th", "10th": "10th", "12th": "12th", "diploma": "diploma",
    "graduate": "graduate", "postgraduate": "postgraduate", "doctorate": "doctorate",
}


def age_on(dob: date, ref: date) -> tuple[int, int, int]:
    """Exact age as (years, months, days) on `ref`."""
    years = ref.year - dob.year
    months = ref.month - dob.month
    days = ref.day - dob.day
    if days < 0:
        months -= 1
        prev_month_end = date(ref.year, ref.month, 1).toordinal() - 1
        days += date.fromordinal(prev_month_end).day
    if months < 0:
        years -= 1
        months += 12
    return years, months, days


def _years_to_ym(value: float) -> tuple[int, int]:
    whole = int(value)
    return whole, round((value - whole) * 12)


def _fmt(t: tuple[int, int, int]) -> str:
    return f"{t[0]} years, {t[1]} months, {t[2]} days"


def _check(rule: str, status: str, detail: str) -> dict:
    return {"rule": rule, "status": status, "detail": detail}  # status: pass | fail | unknown


def evaluate(structured: dict, profile: dict, today: date | None = None) -> dict:
    today = today or date.today()
    checks: list[dict] = []
    missing: list[str] = []

    # 1. Deadline
    last = None
    if structured.get("last_date"):
        try:
            last = date.fromisoformat(structured["last_date"])
        except ValueError:
            last = None
    if last:
        left = (last - today).days
        checks.append(_check("Application deadline", "pass" if left >= 0 else "fail",
                             f"{left} days left (last date {last.isoformat()})" if left >= 0 else f"Deadline passed on {last.isoformat()}"))
    else:
        checks.append(_check("Application deadline", "unknown", "No last date found in the notice."))

    # 2. Age
    age = structured.get("age") or {}
    dob_raw = profile.get("dob")
    if age.get("min") is None and age.get("max") is None:
        checks.append(_check("Age", "unknown", "The notice has no age limit that could be read."))
    elif not dob_raw:
        missing.append("dob")
        checks.append(_check("Age", "unknown", "Add your date of birth to your profile."))
    else:
        dob = date.fromisoformat(dob_raw)
        as_of = date.fromisoformat(age["as_of"]) if age.get("as_of") else (last or today)
        a = age_on(dob, as_of)
        category = (profile.get("category") or "").lower().replace(" ", "")
        relax = 0.0
        notes = []
        for key in {category, *[k for k in ("ex_servicemen",) if profile.get("ex_servicemen_ward")]}:
            if key and key in (age.get("relaxations") or {}):
                relax += float(age["relaxations"][key])
                notes.append(f"{key.upper()} relaxation {age['relaxations'][key]:g} years")
        ok, why = True, []
        if age.get("min") is not None:
            lo = _years_to_ym(age["min"])
            if a[:2] < lo:
                ok = False
                why.append(f"below minimum age {age['min']:g}")
        if age.get("max") is not None:
            hi = _years_to_ym(age["max"] + relax)
            if a[:2] > hi:
                ok = False
                why.append(f"above maximum age {age['max'] + relax:g}")
        detail = f"Your age on {as_of.isoformat()} is {_fmt(a)}."
        if notes:
            detail += " Applied: " + ", ".join(notes) + "."
        if why:
            detail += " Problem: " + "; ".join(why) + "."
        detail += " (Check how the notice words the upper limit.)"
        checks.append(_check("Age", "pass" if ok else "fail", detail))

    # 3. Qualification
    qual = structured.get("qualification") or {}
    required = qual.get("level")
    have = profile.get("qualification")
    if not required:
        checks.append(_check("Qualification", "unknown", "No minimum qualification could be read."))
    elif have not in QUAL_ORDER:
        missing.append("qualification")
        checks.append(_check("Qualification", "unknown", f"The notice needs {QUAL_LABEL.get(required, required)}. Add your highest qualification to your profile."))
    else:
        ok = QUAL_ORDER.index(have) >= QUAL_ORDER.index(required)
        checks.append(_check("Qualification", "pass" if ok else "fail",
                             f"Required: {QUAL_LABEL.get(required, required)}. You have: {QUAL_LABEL.get(have, have)}."))

    # 4. Minimum marks
    min_pct = qual.get("min_percentage")
    if min_pct:
        pct = profile.get("percentage")
        if pct in (None, ""):
            missing.append("percentage")
            checks.append(_check("Minimum marks", "unknown", f"The notice asks for {min_pct:g}%. Add your percentage."))
        else:
            checks.append(_check("Minimum marks", "pass" if float(pct) >= min_pct else "fail",
                                 f"Required {min_pct:g}%. You have {float(pct):g}%."))

    # 5. Gender restriction
    if structured.get("gender"):
        g = (profile.get("gender") or "").lower()
        if not g:
            missing.append("gender")
            checks.append(_check("Gender", "unknown", f"This notice is for {structured['gender']} candidates."))
        else:
            checks.append(_check("Gender", "pass" if g == structured["gender"] else "fail",
                                 f"Notice is for {structured['gender']} candidates."))

    statuses = {c["status"] for c in checks}
    verdict = "not_eligible" if "fail" in statuses else ("needs_info" if "unknown" in statuses else "eligible")
    return {"verdict": verdict, "checks": checks, "missing_profile_fields": sorted(set(missing)),
            "disclaimer": "Automated check from the notice text. Always confirm with the official notice."}
