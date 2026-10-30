from app.services.form_mapper import map_fields

PROFILE = {"full_name": "Rahul Kumar Singh", "father_name": "Rakesh Singh", "dob": "2007-03-10", "gender": "male",
           "state": "Bihar", "email": "r@example.com", "phone": "9876543210", "category": "obc"}


def by_id(results):
    return {r["id"]: r for r in results}


def test_basic_text_fields():
    out = by_id(map_fields([
        {"id": "n", "label": "Name of Candidate", "type": "text"},
        {"id": "f", "label": "Father's Name", "type": "text"},
        {"id": "m", "label": "Mobile No", "type": "tel"},
    ], PROFILE))
    assert out["n"]["value"] == "Rahul Kumar Singh"
    assert out["f"]["value"] == "Rakesh Singh"  # "father" must win over the generic "name"
    assert out["m"]["value"] == "9876543210"


def test_date_format_follows_placeholder():
    out = by_id(map_fields([
        {"id": "a", "label": "Date of Birth", "placeholder": "DD/MM/YYYY", "type": "text"},
        {"id": "b", "label": "Date of Birth", "type": "date"},
        {"id": "c", "label": "DOB", "placeholder": "MM/DD/YYYY", "type": "text"},
    ], PROFILE))
    assert out["a"]["value"] == "10/03/2007"
    assert out["b"]["value"] == "2007-03-10"
    assert out["c"]["value"] == "03/10/2007"


def test_select_matching():
    out = by_id(map_fields([
        {"id": "g", "label": "Gender", "type": "select", "options": [{"value": "M", "label": "Male"}, {"value": "F", "label": "Female"}]},
        {"id": "s", "label": "State", "type": "select", "options": [{"value": "1", "label": "Bengal"}, {"value": "2", "label": "Bihar"}]},
        {"id": "c", "label": "Category", "type": "select", "options": [{"value": "gen", "label": "General"}, {"value": "obc", "label": "OBC"}]},
    ], PROFILE))
    assert out["g"]["value"] == "M" and out["s"]["value"] == "2" and out["c"]["value"] == "obc"


def test_sensitive_fields_are_never_filled():
    out = by_id(map_fields([
        {"id": "p", "label": "Password", "type": "password"},
        {"id": "c", "label": "Enter captcha", "type": "text"},
        {"id": "o", "label": "OTP", "type": "text"},
        {"id": "u", "label": "Upload photo", "type": "file"},
        {"id": "a", "label": "Aadhaar number", "type": "text"},
    ], PROFILE))
    assert all(r["skipped"] and r["value"] is None for r in out.values())


def test_unknown_and_missing_profile_fields_need_review():
    out = by_id(map_fields([
        {"id": "h", "label": "Hobbies", "type": "text"},
        {"id": "pin", "label": "Pin code", "type": "text"},
    ], PROFILE))
    assert out["h"]["value"] is None and out["h"]["needs_review"]
    assert out["pin"]["value"] is None and "not in your profile" in out["pin"]["reason"]


def test_autocomplete_attribute_wins():
    out = by_id(map_fields([{"id": "x", "label": "Something odd", "autocomplete": "given-name", "type": "text"}], PROFILE))
    assert out["x"]["key"] == "first_name" and out["x"]["value"] == "Rahul"
