"""Pure-code calculators for agent tools.

A language model must never do arithmetic (V2 plan section 7.1). Every number
in an eligibility or deadline answer comes from here, and every result carries
its working so the chat can show it.
"""

from __future__ import annotations

from datetime import date

from app.services.eligibility import age_on


def calc_age(dob: date, as_of: date) -> dict:
    y, m, d = age_on(dob, as_of)
    return {"dob": dob.isoformat(), "as_of": as_of.isoformat(), "years": y, "months": m, "days": d,
            "working": f"Born {dob.isoformat()}, age on {as_of.isoformat()} = {y} years, {m} months, {d} days"}


def calc_days_left(target: date, today: date | None = None) -> dict:
    today = today or date.today()
    left = (target - today).days
    return {"today": today.isoformat(), "target": target.isoformat(), "days_left": left,
            "working": f"{target.isoformat()} minus {today.isoformat()} = {left} days"}


def calc_days_between(start: date, end: date) -> dict:
    n = (end - start).days
    return {"start": start.isoformat(), "end": end.isoformat(), "days": n,
            "working": f"{end.isoformat()} minus {start.isoformat()} = {n} days"}


def calc_max_age_with_relaxation(max_age: float, relaxations: dict | None, category: str | None) -> dict:
    relax = float((relaxations or {}).get((category or "").lower().replace(" ", ""), 0) or 0)
    limit = float(max_age) + relax
    return {"category": category, "base_max_age": max_age, "relaxation_years": relax, "effective_max_age": limit,
            "working": f"Maximum age {max_age:g} + {relax:g} years relaxation for {(category or 'general').upper()} = {limit:g} years"}


def calc_fee_total(fees: list[float]) -> dict:
    total = sum(float(f) for f in fees)
    return {"fees": fees, "total": total, "working": " + ".join(f"{f:g}" for f in fees) + f" = {total:g}"}


def calc_percentage(obtained: float, maximum: float) -> dict:
    if maximum <= 0:
        raise ValueError("maximum marks must be above zero")
    pct = round(obtained * 100.0 / maximum, 2)
    return {"obtained": obtained, "maximum": maximum, "percentage": pct,
            "working": f"{obtained:g} / {maximum:g} x 100 = {pct:g}%"}
