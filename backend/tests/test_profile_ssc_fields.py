"""SSC-form profile fields: storage round-trip, reserved keys, form mapping."""

from app.services.form_mapper import map_fields

API = "/api/v1"
SSC_PROFILE = {
    "full_name": "Asha Verma", "father_name": "Ram Verma", "mother_name": "Sita Verma",
    "dob": "2004-08-05", "gender": "female", "category": "obc", "nationality": "Indian",
    "email": "asha@example.com", "phone": "9876543210", "alternate_phone": "9123456780",
    "address_line": "House 12, MG Road", "correspondence_address": "Hostel Block B, Patna", "city": "Patna",
    "district": "Patna", "state": "Bihar", "pincode": "800001",
    "identification_mark": "Mole on left cheek",
    "qualification": "graduate", "qualification_year": 2025, "percentage": 68.5,
    "board_10": "CBSE", "qualification_year_10": 2020, "percentage_10": 85.4,
    "percentage_graduation": 68.5, "ex_serviceman": False, "pwd": False,
}


def test_ssc_profile_fields_round_trip(client, auth):
    r = client.put(f"{API}/profile", headers=auth, json=SSC_PROFILE)
    assert r.status_code == 200, r.text
    saved = client.get(f"{API}/profile", headers=auth).json()
    for key in ("alternate_phone", "district", "board_10", "percentage_10", "percentage_graduation",
                "identification_mark", "correspondence_address"):
        assert saved.get(key) == SSC_PROFILE[key]
    assert saved["ex_serviceman"] is False and saved["pwd"] is False


def test_ssc_keys_are_reserved_for_custom_fields(client, auth):
    r = client.put(f"{API}/profile", headers=auth, json={
        "extra_fields": [{"key": "percentage_10", "label": "Percentage 10", "type": "number", "value": 50}]})
    assert r.status_code == 422


def _field(id_, name, label, type="text", options=None, placeholder=""):
    return {"id": id_, "name": name, "label": label, "type": type, "placeholder": placeholder,
            "autocomplete": "", "pattern": "", "options": options or [], "index": 0}


def test_mapper_fills_ssc_sample_fields():
    profile = {k: v for k, v in SSC_PROFILE.items() if v != ""}
    fields = [
        _field("cand_name", "candidate_name", "Name of Candidate (As per Matriculation Certificate)"),
        _field("father_name", "father_name", "Father's Name"),
        _field("dob", "dob", "Date of Birth", placeholder="DD/MM/YYYY"),
        _field("mobile", "mobile", "Mobile Number (10 digit, for OTP & alerts)", "tel"),
        _field("alt_mobile", "alternate_mobile", "Alternate Mobile Number", "tel"),
        _field("perm_addr", "permanent_address", "Permanent Address", "textarea"),
        _field("district", "district", "District"),
        _field("state", "state", "State / UT", "select",
               [{"value": "Bihar", "label": "Bihar"}, {"value": "Delhi", "label": "Delhi"}]),
        _field("board10", "board_10", "Class 10th Board / University"),
        _field("year10", "year_of_passing_10", "Year of Passing (10th)"),
        _field("pct10", "percentage_10", "Percentage of Marks (10th)"),
        _field("pct_grad", "percentage_graduation", "Percentage of Marks (Graduation)"),
        _field("id_mark", "identification_mark", "Visible Identification Mark"),
        _field("gender", "gender", "Gender", "radio",
               [{"value": "Male", "label": "Male"}, {"value": "Female", "label": "Female"}]),
        _field("exs", "ex_serviceman", "Are you an Ex-Serviceman?", "radio",
               [{"value": "Yes", "label": "Yes"}, {"value": "No", "label": "No"}]),
        _field("pwd", "pwd", "Are you a PwD (Divyangjan) candidate?", "radio",
               [{"value": "Yes", "label": "Yes"}, {"value": "No", "label": "No"}]),
        _field("captcha", "captcha", "Captcha"),
        _field("roll10", "roll_10", "Class 10th Roll Number"),
    ]
    out = {r["id"]: r for r in map_fields(fields, profile)}
    assert out["cand_name"]["value"] == "Asha Verma"
    assert out["dob"]["value"] == "05/08/2004"
    assert out["alt_mobile"]["value"] == "9123456780"
    assert out["district"]["value"] == "Patna"
    assert out["state"]["value"] == "Bihar"
    assert out["board10"]["value"] == "CBSE"
    assert out["pct10"]["value"] == "85.4"
    assert out["pct_grad"]["value"] == "68.5"
    assert out["id_mark"]["value"] == "Mole on left cheek"
    assert out["gender"]["value"] == "Female"
    assert out["exs"]["value"] == "No" and out["pwd"]["value"] == "No"
    # Safety invariants: captcha and roll numbers are never auto-filled.
    assert out["captcha"]["skipped"] is True
    assert out["roll10"]["value"] is None
