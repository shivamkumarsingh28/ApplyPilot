"""Dynamic profile fields + custom vault document types."""

import io

from PIL import Image


def _put_profile(client, auth, extra):
    r = client.put("/api/v1/profile", json={"full_name": "Asha Verma", "extra_fields": extra}, headers=auth)
    return r


def test_extra_fields_roundtrip_and_fill_a_form_field(client, auth):
    extra = [{"key": "blood_group", "label": "Blood group", "type": "select",
              "options": ["A+", "B+", "O+"], "value": "B+"},
             {"key": "mother_tongue", "label": "Mother tongue", "type": "text", "options": [], "value": "Hindi"}]
    r = _put_profile(client, auth, extra)
    assert r.status_code == 200, r.text
    assert [f["key"] for f in r.json()["extra_fields"]] == ["blood_group", "mother_tongue"]
    got = client.get("/api/v1/profile", headers=auth).json()
    assert got["extra_fields"][0]["value"] == "B+"

    # The form mapper offers custom values on matching labels — flagged for review.
    from app.services.form_mapper import map_fields

    profile = client.get("/api/v1/profile", headers=auth).json()
    fields = [{"index": 0, "id": "bg", "name": "blood_group", "label": "Blood Group", "type": "select",
               "options": [{"value": "B+", "label": "B+"}, {"value": "O+", "label": "O+"}]},
              {"index": 1, "id": "mt", "name": "mt", "label": "Mother Tongue", "type": "text"}]
    out = {m["id"]: m for m in map_fields(fields, profile)}
    assert out["bg"]["value"] == "B+" and out["bg"]["needs_review"] is True
    assert out["mt"]["value"] == "Hindi" and out["mt"]["needs_review"] is True


def test_extra_fields_validation_and_safety(client, auth):
    bad_cases = [
        [{"key": "dob", "label": "Other DOB", "type": "text", "value": "x"}],  # reserved key
        [{"key": "aadhaar_no", "label": "Number", "type": "text", "value": "x"}],  # sensitive key
        [{"key": "ok_field", "label": "Passport number", "type": "text", "value": "x"}],  # sensitive label
        [{"key": "n", "label": "Count", "type": "number", "value": "abc"}],  # number must be a number
        [{"key": "d", "label": "When", "type": "date", "value": "31/12/2026"}],  # date must be ISO
        [{"key": "s", "label": "Pick", "type": "select", "options": ["a"], "value": "b"}],  # not an option
        [{"key": "dup", "label": "One", "type": "text", "value": "1"},
         {"key": "dup", "label": "Two", "type": "text", "value": "2"}],  # duplicate keys
        [{"key": f"f{i:02d}", "label": f"F{i}", "type": "text", "value": "x"} for i in range(31)],  # max 30
    ]
    for extra in bad_cases:
        r = _put_profile(client, auth, extra)
        assert r.status_code == 422, (extra, r.text)


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), (200, 200, 200)).save(buf, "PNG")
    return buf.getvalue()


def test_custom_document_type(client, auth):
    r = client.post("/api/v1/documents",
                    files={"file": ("income.pdf", b"%PDF-1.4 fake", "application/pdf")},
                    data={"kind": "other", "custom_kind": "Income Certificate"}, headers=auth)
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["kind"] == "other" and doc["custom_kind"] == "Income Certificate"
    listed = client.get("/api/v1/documents", headers=auth).json()
    assert listed[0]["custom_kind"] == "Income Certificate"
    # Copy keeps the custom name.
    copy = client.post(f"/api/v1/documents/{doc['id']}/copy", headers=auth)
    assert copy.status_code == 201 and copy.json()["custom_kind"] == "Income Certificate"
    # Sensitive type names are refused.
    bad = client.post("/api/v1/documents",
                      files={"file": ("x.pdf", b"%PDF-1.4 fake", "application/pdf")},
                      data={"kind": "other", "custom_kind": "Aadhaar card"}, headers=auth)
    assert bad.status_code == 422
    # custom_kind is ignored for a known kind (engine vocabulary stays clean).
    known = client.post("/api/v1/documents",
                        files={"file": ("p.png", _png(), "image/png")},
                        data={"kind": "photo", "custom_kind": "Income Certificate"}, headers=auth)
    assert known.status_code == 201 and known.json()["custom_kind"] == ""
