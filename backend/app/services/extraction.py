"""Structured extraction from a notice.

Two layers, on purpose:

1. `rule_extract` - regex rules that read the common wording of Indian and
   international job/admission notices. Deterministic, free, testable.
2. `llm_extract` - asks the configured model (Muse Spark) for the same JSON
   schema, then `merge` combines the two. Where both disagree we keep the rule
   value and list the disagreement under `needs_review`, so the user sees it.

Dates, ages and fees decide whether someone applies, so we never let a model's
guess silently overwrite a value that matched an explicit pattern.
"""

from __future__ import annotations

import json
import re
from datetime import date

from app.services.llm.factory import get_llm

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], start=1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
MONTHS["sept"] = 9

DATE_TEXT = r"(\d{1,2})(?:st|nd|rd|th)?[\s\-/,]+([A-Za-z]{3,9})\.?[\s\-/,]+(\d{4})"
DATE_NUM = r"(\d{1,2})[\-/.](\d{1,2})[\-/.](\d{4})"

QUAL_ORDER = ["below_10th", "10th", "12th", "diploma", "graduate", "postgraduate", "doctorate"]

DOC_KEYWORDS = {
    "photo": ["photograph", "passport size photo", "passport-size photo"],
    "signature": ["signature"],
    "marksheet_10": ["class 10", "10th certificate", "matriculation certificate", "high school certificate"],
    "marksheet_12": ["class 12", "12th certificate", "intermediate certificate", "10+2 certificate"],
    "degree": ["degree certificate", "graduation certificate", "provisional certificate"],
    "caste_certificate": ["caste certificate", "category certificate", "obc certificate", "sc/st certificate"],
    "domicile": ["domicile", "residence certificate", "residential certificate"],
    "id_proof": ["id proof", "identity proof", "photo id"],
    "birth_certificate": ["birth certificate", "date of birth proof"],
}

STAGE_KEYWORDS = [
    ("written examination", "Written exam"), ("written exam", "Written exam"),
    ("physical fitness", "Physical fitness test"), ("physical test", "Physical fitness test"),
    ("medical", "Medical examination"), ("interview", "Interview"),
    ("document verification", "Document verification"), ("skill test", "Skill test"),
]


def parse_date(text: str) -> date | None:
    m = re.search(DATE_TEXT, text)
    if m:
        month = MONTHS.get(m.group(2).lower())
        if month:
            try:
                return date(int(m.group(3)), month, int(m.group(1)))
            except ValueError:
                return None
    m = re.search(DATE_NUM, text)
    if m:  # day-first, the convention in India and most of the world
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return None


def _find_date_after(text: str, keywords: list[str], window: int = 160) -> date | None:
    low = text.lower()
    for kw in keywords:
        for m in re.finditer(re.escape(kw), low):
            d = parse_date(text[m.end(): m.end() + window])
            if d:
                return d
    return None


def _age_info(text: str) -> dict:
    out: dict = {"min": None, "max": None, "as_of": None, "relaxations": {}}
    m = re.search(r"between\s+(\d{2}(?:\.\d)?)\s*(?:and|to|-|–)\s*(\d{2}(?:\.\d)?)\s*years", text, re.I)
    if not m:
        m = re.search(r"(?:age|aged)[^.\n]{0,40}?(\d{2}(?:\.\d)?)\s*(?:to|-|–)\s*(\d{2}(?:\.\d)?)\s*years", text, re.I)
    if m:
        out["min"], out["max"] = float(m.group(1)), float(m.group(2))
    else:
        lo = re.search(r"(?:minimum age|not less than)[^\d]{0,25}(\d{2}(?:\.\d)?)", text, re.I)
        hi = re.search(r"(?:maximum age|not (?:more|above) than|upper age limit)[^\d]{0,25}(\d{2}(?:\.\d)?)", text, re.I)
        out["min"] = float(lo.group(1)) if lo else None
        out["max"] = float(hi.group(1)) if hi else None
    asof = re.search(r"as\s+on\s+(.{0,30})", text, re.I)
    if asof:
        d = parse_date(asof.group(1))
        out["as_of"] = d.isoformat() if d else None
    pat = re.compile(
        r"(SC\s*/\s*ST|SC|ST|OBC|EWS|PwD|PH|ex-?servicem[ae]n|wards? of ex-?servicem[ae]n)"
        r"[^\d\n;]{0,40}?(\d+(?:\.\d+)?)\s*years?", re.I)
    for m in pat.finditer(text):
        label, years = m.group(1).lower(), float(m.group(2))
        keys = ["sc", "st"] if label.replace(" ", "") == "sc/st" else [
            "ex_servicemen" if "servicem" in label else label.replace(" ", "")]
        for k in keys:
            out["relaxations"][k] = years
    return out


def _qualification(text: str) -> dict:
    level = None
    checks = [
        ("doctorate", r"\bph\.?d\b|doctorate"),
        ("postgraduate", r"post[\s-]?graduate|master'?s degree|\bm\.?(?:a|sc|com|tech)\b"),
        ("graduate", r"graduat|bachelor|\bb\.?(?:a|sc|com|tech|e)\b|degree"),
        ("diploma", r"diploma"),
        ("12th", r"10\s*\+\s*2|12th|class\s*(?:12|xii)|intermediate|higher secondary"),
        ("10th", r"10th|class\s*(?:10|x)\b|matric|secondary school"),
    ]
    m_qual = re.search(r"(?:educational )?qualification[:\s].{0,200}", text, re.I | re.S)
    scope = (m_qual.group(0) if m_qual else text).lower()
    for lv, pat in checks:
        if re.search(pat, scope):
            level = lv
            break
    pct = None
    m = re.search(r"(?:minimum|at least|not less than)?[^.\n]{0,40}?(\d{2}(?:\.\d+)?)\s*(?:%|per\s?cent)", scope)
    if m:
        pct = float(m.group(1))
    return {"level": level, "min_percentage": pct, "text": (m_qual.group(0).split("\n")[0].strip() if m_qual else "")}


def _fee(text: str) -> dict | None:
    m = re.search(r"(?:fee|fees|charges)[^.\n]{0,60}?(?:rs\.?|inr|₹)\s*([\d,]+)", text, re.I) or \
        re.search(r"(?:rs\.?|inr|₹)\s*([\d,]+)[^.\n]{0,40}?(?:fee|fees)", text, re.I)
    if not m:
        return None
    return {"amount": int(m.group(1).replace(",", "")), "currency": "INR"}


def _image_spec(text: str, keywords: list[str]) -> dict | None:
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if any(k in line.lower() for k in keywords):
            window = " ".join(lines[i: i + 2])
            dim = re.search(r"(\d{2,4})\s*(?:x|×|by)\s*(\d{2,4})", window, re.I)
            kb = re.search(r"(\d{1,4})\s*(?:kb)?\s*(?:to|-|–)\s*(\d{1,4})\s*kb", window, re.I)
            if dim or kb:
                spec = {"width": None, "height": None, "min_kb": None, "max_kb": None,
                        "format": "jpg", "background": "white"}
                if dim:
                    spec["width"], spec["height"] = int(dim.group(1)), int(dim.group(2))
                if kb:
                    spec["min_kb"], spec["max_kb"] = int(kb.group(1)), int(kb.group(2))
                else:
                    mx = re.search(r"(?:up to|max(?:imum)?|below|under)\s*(\d{1,4})\s*kb", window, re.I)
                    spec["max_kb"] = int(mx.group(1)) if mx else None
                if "png" in window.lower():
                    spec["format"] = "png"
                return spec
    return None


def rule_extract(text: str) -> dict:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    low = text.lower()
    last = _find_date_after(text, ["last date", "closing date", "last day", "apply before", "deadline"])
    gender = None
    if re.search(r"only\s+(?:for\s+)?(?:female|women)", low):
        gender = "female"
    elif re.search(r"only\s+(?:for\s+)?(?:male|men)\b", low):
        gender = "male"
    docs = [k for k, kws in DOC_KEYWORDS.items() if any(kw in low for kw in kws)]
    stages: list[str] = []
    for kw, label in STAGE_KEYWORDS:
        if kw in low and label not in stages:
            stages.append(label)
    org = next((ln for ln in lines[:6] if re.search(r"board|commission|ministry|department|bank|university|army|navy|force|services", ln, re.I)), None)
    return {
        "title": lines[0][:200] if lines else "Untitled notice",
        "organisation": org,
        "last_date": last.isoformat() if last else None,
        "age": _age_info(text),
        "qualification": _qualification(text),
        "fee": _fee(text),
        "gender": gender,
        "documents": docs,
        "photo_spec": _image_spec(text, ["photograph", "photo "]),
        "signature_spec": _image_spec(text, ["signature specification", "signature:", "signature size", "signature must"]),
        "selection_stages": stages,
        "needs_review": [],
        "method": "rules",
    }


SCHEMA_HINT = {
    "title": "string", "organisation": "string|null", "last_date": "YYYY-MM-DD|null",
    "age": {"min": "number|null", "max": "number|null", "as_of": "YYYY-MM-DD|null",
            "relaxations": {"sc": "years", "st": "years", "obc": "years"}},
    "qualification": {"level": "below_10th|10th|12th|diploma|graduate|postgraduate|doctorate|null",
                      "min_percentage": "number|null", "text": "string"},
    "fee": {"amount": "number", "currency": "string"},
    "gender": "male|female|null", "documents": ["photo|signature|marksheet_10|marksheet_12|degree|caste_certificate|domicile|id_proof|birth_certificate"],
    "photo_spec": {"width": "px", "height": "px", "min_kb": "number|null", "max_kb": "number|null", "format": "jpg|png", "background": "string"},
    "signature_spec": "same shape as photo_spec or null", "selection_stages": ["string"],
}


def llm_extract(text: str) -> dict | None:
    llm = get_llm()
    if llm.offline:
        return None
    prompt = (
        "You extract facts from a recruitment or admission notice. Use ONLY the notice text. "
        "If a field is not stated, use null. Never guess dates, ages or fees. "
        f"Return one JSON object with exactly this shape: {json.dumps(SCHEMA_HINT)}\n\nNOTICE:\n{text[:120000]}"
    )
    try:
        raw = llm.chat([{"role": "user", "content": prompt}], json_mode=True, temperature=0.0, max_tokens=2000)
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _empty(v) -> bool:
    return v in (None, "", [], {}) or (isinstance(v, dict) and all(_empty(x) for x in v.values()))


def merge(rules: dict, llm: dict | None) -> dict:
    """Fill gaps in `rules` with `llm`; report disagreements instead of overwriting."""
    if not llm:
        return rules
    out = dict(rules)
    review: list[dict] = []
    for key in ("organisation", "last_date", "gender", "fee", "photo_spec", "signature_spec"):
        a, b = rules.get(key), llm.get(key)
        if _empty(a) and not _empty(b):
            out[key] = b
        elif not _empty(a) and not _empty(b) and a != b:
            review.append({"field": key, "rules": a, "model": b})
    for key in ("age", "qualification"):
        a, b = dict(rules.get(key) or {}), llm.get(key) or {}
        if isinstance(b, dict):
            for sub, val in b.items():
                if _empty(a.get(sub)) and not _empty(val):
                    a[sub] = val
                elif not _empty(a.get(sub)) and not _empty(val) and a.get(sub) != val and sub != "text":
                    review.append({"field": f"{key}.{sub}", "rules": a.get(sub), "model": val})
        out[key] = a
    docs = list(dict.fromkeys((rules.get("documents") or []) + [d for d in (llm.get("documents") or []) if isinstance(d, str)]))
    out["documents"] = docs
    if not rules.get("selection_stages") and llm.get("selection_stages"):
        out["selection_stages"] = llm["selection_stages"]
    out["needs_review"] = review
    out["method"] = "rules+model"
    return out


def extract_structured(text: str) -> dict:
    return merge(rule_extract(text), llm_extract(text))
