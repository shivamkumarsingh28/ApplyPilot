from datetime import date

from app.services.eligibility import age_on, evaluate
from app.services.extraction import rule_extract


def test_age_on_exact():
    assert age_on(date(2007, 3, 10), date(2026, 10, 1)) == (19, 6, 21)
    assert age_on(date(2000, 2, 29), date(2001, 2, 28)) == (0, 11, 30)


def _structured(sample_text):
    return rule_extract(sample_text)


def test_eligible_candidate(sample_text):
    p = {"dob": "2007-03-10", "category": "obc", "qualification": "10th", "percentage": 62}
    r = evaluate(_structured(sample_text), p, today=date(2026, 10, 29))
    assert r["verdict"] == "eligible"


def test_too_old_without_relaxation(sample_text):
    p = {"dob": "2004-01-01", "category": "general", "qualification": "12th", "percentage": 70}
    r = evaluate(_structured(sample_text), p, today=date(2026, 10, 29))
    assert r["verdict"] == "not_eligible"
    assert any(c["rule"] == "Age" and c["status"] == "fail" for c in r["checks"])


def test_relaxation_makes_same_person_eligible(sample_text):
    p = {"dob": "2004-01-01", "category": "sc", "qualification": "12th", "percentage": 70}
    r = evaluate(_structured(sample_text), p, today=date(2026, 10, 29))
    assert r["verdict"] == "eligible"


def test_deadline_passed(sample_text):
    p = {"dob": "2007-03-10", "qualification": "10th", "percentage": 62}
    r = evaluate(_structured(sample_text), p, today=date(2026, 12, 1))
    assert r["verdict"] == "not_eligible"


def test_missing_profile_needs_info(sample_text):
    r = evaluate(_structured(sample_text), {}, today=date(2026, 10, 29))
    assert r["verdict"] == "needs_info"
    assert {"dob", "qualification"} <= set(r["missing_profile_fields"])


def test_marks_below_minimum(sample_text):
    p = {"dob": "2007-03-10", "qualification": "10th", "percentage": 40}
    r = evaluate(_structured(sample_text), p, today=date(2026, 10, 29))
    assert any(c["rule"] == "Minimum marks" and c["status"] == "fail" for c in r["checks"])
