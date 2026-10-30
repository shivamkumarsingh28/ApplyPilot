from app.services.extraction import merge, parse_date, rule_extract


def test_sample_notice_core_fields(sample_text):
    s = rule_extract(sample_text)
    assert s["last_date"] == "2026-11-14"
    assert s["age"]["min"] == 17.5 and s["age"]["max"] == 21.0
    assert s["age"]["as_of"] == "2026-10-01"
    assert s["age"]["relaxations"] == {"sc": 3.0, "st": 3.0, "obc": 2.0, "ex_servicemen": 1.0}
    assert s["qualification"]["level"] == "10th" and s["qualification"]["min_percentage"] == 45.0
    assert s["fee"] == {"amount": 250, "currency": "INR"}


def test_image_specs(sample_text):
    s = rule_extract(sample_text)
    assert (s["photo_spec"]["width"], s["photo_spec"]["height"], s["photo_spec"]["min_kb"], s["photo_spec"]["max_kb"]) == (200, 230, 20, 50)
    assert (s["signature_spec"]["width"], s["signature_spec"]["height"], s["signature_spec"]["max_kb"]) == (140, 60, 20)


def test_documents_and_stages(sample_text):
    s = rule_extract(sample_text)
    assert {"photo", "signature", "marksheet_10", "caste_certificate", "domicile"} <= set(s["documents"])
    assert "Physical fitness test" in s["selection_stages"]


def test_date_formats():
    assert str(parse_date("14th November, 2026")) == "2026-11-14"
    assert str(parse_date("14/11/2026")) == "2026-11-14"
    assert str(parse_date("5 Sept 2026")) == "2026-09-05"
    assert parse_date("no date here") is None


def test_other_age_wording():
    s = rule_extract("Last date: 01-12-2026. Minimum age 18 years and maximum age 27 years as on 01/01/2026.")
    assert s["age"]["min"] == 18.0 and s["age"]["max"] == 27.0
    assert s["last_date"] == "2026-12-01"


def test_merge_keeps_rule_value_and_flags_disagreement():
    rules = {"last_date": "2026-11-14", "organisation": None, "age": {"min": 18, "max": 25}, "qualification": {}, "documents": ["photo"], "selection_stages": []}
    model = {"last_date": "2026-11-15", "organisation": "Some Board", "age": {"min": 18, "max": 30}, "documents": ["signature"]}
    out = merge(rules, model)
    assert out["last_date"] == "2026-11-14"  # rule match is not overwritten
    assert out["organisation"] == "Some Board"  # gap filled by the model
    assert {r["field"] for r in out["needs_review"]} == {"last_date", "age.max"}
    assert out["documents"] == ["photo", "signature"]
