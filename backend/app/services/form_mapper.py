"""Maps the fields of a web form to values from the user's profile.

The browser extension scans a page and sends field descriptors here (label,
name, id, placeholder, type, autocomplete, options). We answer with a value and
a confidence per field. High-confidence fields are filled; low-confidence ones
are highlighted for the user to confirm. We never touch passwords, file inputs,
captcha or one-time-code fields.

Matching order:  autocomplete attribute  >  longest phrase match  >  token fuzzy match
                 >  (optional) model suggestion, always flagged for review.
"""

from __future__ import annotations

import difflib
import json
import re
from datetime import date

from app.services.llm.factory import get_llm

AUTOCOMPLETE = {
    "name": "full_name", "given-name": "first_name", "family-name": "last_name", "email": "email", "tel": "phone",
    "tel-national": "phone", "bday": "dob", "sex": "gender", "postal-code": "pincode", "address-line1": "address_line",
    "street-address": "address_line", "address-level2": "city", "address-level1": "state", "country-name": "nationality",
}

SYNONYMS: dict[str, list[str]] = {
    "full_name": ["full name", "name of candidate", "candidate name", "applicant name", "your name", "name as per", "name"],
    "first_name": ["first name", "given name", "forename"],
    "last_name": ["last name", "surname", "family name"],
    "father_name": ["father's name", "fathers name", "father name", "name of father", "father"],
    "mother_name": ["mother's name", "mothers name", "mother name", "name of mother", "mother"],
    "dob": ["date of birth", "birth date", "dob", "d.o.b", "birthday"],
    "gender": ["gender", "sex"],
    "category": ["category", "caste category", "reservation category", "social category"],
    "nationality": ["nationality", "citizenship"],
    "email": ["email address", "e-mail", "email", "mail id"],
    "phone": ["mobile number", "mobile no", "phone number", "contact number", "mobile", "phone", "cell"],
    "address_line": ["address line 1", "permanent address", "correspondence address", "street address", "address"],
    "city": ["city", "town", "village"],
    "state": ["state", "province"],
    "pincode": ["pin code", "pincode", "postal code", "zip code", "zip", "pin"],
    "qualification": ["highest qualification", "educational qualification", "qualification", "education level"],
    "percentage": ["percentage", "marks obtained", "aggregate marks", "marks"],
    "qualification_year": ["year of passing", "passing year"],
}
_PHRASES = sorted(((k, p) for k, ps in SYNONYMS.items() for p in ps), key=lambda kp: -len(kp[1]))

SKIP_TYPES = {"password", "file", "submit", "button", "hidden", "image", "reset", "checkbox"}
SKIP_WORDS = re.compile(r"captcha|otp|one.?time|verification code|security code|cvv|card number|password|aadhaar|aadhar|passport no|pan\b", re.I)


def _idx(f: dict, i: int) -> int:
    """Position of a field on the page; falls back to list order when the client sent null."""
    return f["index"] if f.get("index") is not None else i


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9' ]+", " ", (s or "").lower().replace("_", " ").replace("-", " ")).strip()


def _field_text(f: dict) -> str:
    return _norm(" ".join(str(f.get(k) or "") for k in ("label", "placeholder", "name", "id", "ariaLabel", "title")))


def match_field(f: dict) -> tuple[str | None, float, str]:
    ac = (f.get("autocomplete") or "").split(" ")[-1]
    if ac in AUTOCOMPLETE:
        return AUTOCOMPLETE[ac], 0.98, "autocomplete attribute"
    text = _field_text(f)
    for key, phrase in _PHRASES:
        if re.search(rf"(?<![a-z]){re.escape(_norm(phrase))}(?![a-z])", text):
            words = len(phrase.split())
            conf = 0.92 if words >= 2 else (0.62 if phrase == "name" else 0.78)
            return key, conf, f'label matches "{phrase}"'
    tokens = set(text.split())
    best, best_score = None, 0.0
    for key, phrases in SYNONYMS.items():
        for p in phrases:
            ptoks = set(_norm(p).split())
            if ptoks and ptoks <= tokens:
                continue
            r = difflib.SequenceMatcher(None, text, _norm(p)).ratio()
            if r > best_score:
                best, best_score = key, r
    if best and best_score >= 0.8:
        return best, 0.5, "fuzzy label match"
    return None, 0.0, "no match"


def _format_date(iso: str, f: dict) -> str:
    try:
        d = date.fromisoformat(iso)
    except (ValueError, TypeError):
        return iso
    if (f.get("type") or "").lower() == "date":
        return d.isoformat()
    hint = " ".join(str(f.get(k) or "") for k in ("placeholder", "pattern", "label", "title")).lower()
    sep = "-" if re.search(r"dd-mm|d-m|dd-mon", hint) else "/"
    if re.search(r"yyyy[-/]mm[-/]dd", hint):
        return d.isoformat().replace("-", sep if sep != "-" else "-")
    if re.search(r"mm[-/]dd[-/]yyyy", hint):
        return f"{d.month:02d}{sep}{d.day:02d}{sep}{d.year}"
    return f"{d.day:02d}{sep}{d.month:02d}{sep}{d.year}"


def _pick_option(value: str, options: list[dict]) -> str | None:
    """Choose the option whose value or label best matches `value`; None if unsure."""
    target = _norm(value)
    labelled = [(o, _norm(o.get("label") or "")) for o in options] + [(o, _norm(o.get("value") or "")) for o in options]
    for o, t in labelled:
        if t and t == target:
            return o.get("value")
    for o, t in labelled:
        if t and (t.startswith(target) or target.startswith(t)) and len(min(t, target, key=len)) >= 1 and len(t) >= 1:
            if len(t) >= 2 and len(target) >= 2:
                return o.get("value")
    cands = [t for _, t in labelled if t]
    close = difflib.get_close_matches(target, cands, n=1, cutoff=0.78)
    if close:
        return next(o.get("value") for o, t in labelled if t == close[0])
    return None


def _derive(profile: dict) -> dict:
    p = dict(profile)
    name = (p.get("full_name") or "").strip()
    if name and not p.get("first_name"):
        parts = name.split()
        p["first_name"], p["last_name"] = parts[0], " ".join(parts[1:]) if len(parts) > 1 else ""
    if not name and p.get("first_name"):
        p["full_name"] = f"{p['first_name']} {p.get('last_name', '')}".strip()
    return p


def _llm_suggest(unmatched: list[dict]) -> dict[str, str]:
    """Optional: let the model propose a profile key for fields the rules missed."""
    llm = get_llm()
    if llm.offline or not unmatched:
        return {}
    prompt = (
        "Match each form field to the best profile key, or null if none fits. "
        f"Allowed keys: {sorted(SYNONYMS)}. Fields: "
        + json.dumps([{"id": f.get("id") or f.get("name"), "label": f.get("label"), "placeholder": f.get("placeholder"), "name": f.get("name")} for f in unmatched])
        + '\nReturn JSON like {"<id>": "<key or null>"} and nothing else.'
    )
    try:
        data = json.loads(llm.chat([{"role": "user", "content": prompt}], json_mode=True, temperature=0.0, max_tokens=800))
    except Exception:
        return {}
    return {k: v for k, v in data.items() if isinstance(v, str) and v in SYNONYMS}


def map_fields(fields: list[dict], profile: dict) -> list[dict]:
    prof = _derive(profile)
    results: list[dict] = []
    unmatched: list[dict] = []
    keyed: dict[str, tuple[str, float, str]] = {}

    for i, f in enumerate(fields):
        fid = f.get("id") or f.get("name") or f"field-{i}"
        ftype = (f.get("type") or "text").lower()
        if ftype in SKIP_TYPES or SKIP_WORDS.search(_field_text(f)):
            results.append({"id": fid, "index": _idx(f, i), "key": None, "value": None, "confidence": 0.0,
                            "needs_review": False, "skipped": True, "reason": "Never filled automatically (password, file, captcha, ID or payment field)."})
            continue
        key, conf, why = match_field(f)
        if key is None:
            unmatched.append(f)
        keyed[fid] = (key, conf, why)

    suggestions = _llm_suggest(unmatched)
    for i, f in enumerate(fields):
        fid = f.get("id") or f.get("name") or f"field-{i}"
        if fid not in keyed:
            continue
        key, conf, why = keyed[fid]
        if key is None and fid in suggestions:
            key, conf, why = suggestions[fid], 0.55, "model suggestion"
        out = {"id": fid, "index": _idx(f, i), "key": key, "value": None, "confidence": conf, "needs_review": True, "skipped": False, "reason": why}
        if key is None:
            out["reason"] = "No matching profile field."
        else:
            raw = prof.get(key)
            if raw in (None, ""):
                out["reason"] = f"'{key}' is not in your profile yet."
            else:
                value = raw
                if key == "dob":
                    value = _format_date(str(raw), f)
                options = f.get("options") or []
                if options:
                    picked = _pick_option(str(raw), options)
                    value = picked
                    if picked is None:
                        out["reason"] = f"Could not match '{raw}' to the dropdown options."
                if value is not None:
                    out["value"] = str(value)
                    out["needs_review"] = conf < 0.75
        results.append(out)
    results.sort(key=lambda r: r["index"])
    return results
