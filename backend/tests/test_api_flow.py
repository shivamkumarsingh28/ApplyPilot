"""End-to-end flow through the real HTTP API with the offline mock model."""

import base64
import io

from PIL import Image

from tests.conftest import make_jpeg, make_signature_jpeg

API = "/api/v1"


def test_health(client):
    r = client.get(f"{API}/health")
    assert r.status_code == 200 and r.json()["llm"]["offline"] is True


def test_auth_rules(client):
    body = {"email": "x@example.com", "password": "password123"}
    assert client.post(f"{API}/auth/register", json=body).status_code == 201
    assert client.post(f"{API}/auth/register", json=body).status_code == 409
    assert client.post(f"{API}/auth/login", json={**body, "password": "wrongpass1"}).status_code == 401
    assert client.get(f"{API}/profile").status_code == 401
    assert client.post(f"{API}/auth/register", json={"email": "y@example.com", "password": "short"}).status_code == 422


def test_profile_roundtrip_and_validation(client, auth):
    r = client.put(f"{API}/profile", headers=auth, json={"dob": "2007-03-10", "category": "OBC", "qualification": "10th", "percentage": 62})
    assert r.status_code == 200 and r.json()["category"] == "obc"
    assert client.get(f"{API}/profile", headers=auth).json()["dob"] == "2007-03-10"
    assert client.put(f"{API}/profile", headers=auth, json={"dob": "not-a-date"}).status_code == 422
    assert client.put(f"{API}/profile", headers=auth, json={"aadhaar": "123"}).status_code == 422  # unknown/sensitive fields rejected


def test_full_notice_flow(client, auth, sample_text):
    client.put(f"{API}/profile", headers=auth, json={"dob": "2007-03-10", "category": "obc", "qualification": "10th", "percentage": 62, "gender": "male"})
    r = client.post(f"{API}/notices", headers=auth, data={"text": sample_text})
    assert r.status_code == 201, r.text
    notice = r.json()
    nid = notice["id"]
    assert notice["structured"]["last_date"] == "2026-11-14"
    assert notice["scam_report"]["level"] == "low"

    a = client.post(f"{API}/notices/{nid}/ask", headers=auth, json={"question": "Is there a physical fitness test?"}).json()
    assert "physical" in a["answer"].lower() and a["citations"] and a["mode"] == "extractive"
    miss = client.post(f"{API}/notices/{nid}/ask", headers=auth, json={"question": "What is the salary of astronauts on Mars?"}).json()
    assert miss["mode"] == "not_found"

    elig = client.get(f"{API}/notices/{nid}/eligibility", headers=auth).json()
    assert elig["verdict"] in ("eligible", "not_eligible")  # depends on today's date vs the sample deadline
    assert any(c["rule"] == "Age" and c["status"] == "pass" for c in elig["checks"])

    ready = client.get(f"{API}/notices/{nid}/readiness", headers=auth).json()
    assert ready["percent"] == 0 and len(ready["missing"]) >= 3

    tracker = client.get(f"{API}/applications", headers=auth).json()
    assert tracker[0]["notice_id"] == nid and tracker[0]["deadline"] == "2026-11-14"


def test_photo_from_notice_spec_saved_to_vault_improves_readiness(client, auth, sample_text):
    nid = client.post(f"{API}/notices", headers=auth, data={"text": sample_text}).json()["id"]
    r = client.post(f"{API}/photo/process", headers=auth, data={"kind": "photo", "notice_id": nid, "save_to_vault": "true"},
                    files={"file": ("me.jpg", make_jpeg(), "image/jpeg")})
    assert r.status_code == 200, r.text
    body = r.json()
    img = Image.open(io.BytesIO(base64.b64decode(body["data_base64"])))
    assert img.size == (200, 230) and body["report"]["ok"] and body["document_id"]
    r2 = client.post(f"{API}/photo/process", headers=auth, data={"kind": "signature", "notice_id": nid, "save_to_vault": "true"},
                     files={"file": ("sig.jpg", make_signature_jpeg(), "image/jpeg")})
    assert r2.json()["report"]["ok"]
    ready = client.get(f"{API}/notices/{nid}/readiness", headers=auth).json()
    assert {h["kind"] for h in ready["have"]} == {"photo", "signature"}


def test_documents_are_encrypted_on_disk_and_private(client, auth, tmp_path):
    secret = b"MY-SECRET-MARKSHEET-CONTENT"
    r = client.post(f"{API}/documents", headers=auth, data={"kind": "marksheet_10"}, files={"file": ("m.txt", secret, "text/plain")})
    assert r.status_code == 201
    doc_id = r.json()["id"]
    on_disk = [p for p in (tmp_path / "files").rglob("*.enc")]
    assert on_disk and secret not in on_disk[0].read_bytes()
    assert client.get(f"{API}/documents/{doc_id}/download", headers=auth).content == secret
    other = client.post(f"{API}/auth/register", json={"email": "b@example.com", "password": "password123"}).json()["access_token"]
    assert client.get(f"{API}/documents/{doc_id}/download", headers={"Authorization": f"Bearer {other}"}).status_code == 404
    assert client.post(f"{API}/documents", headers=auth, data={"kind": "other"}, files={"file": ("x.exe", b"MZ", "application/x-msdownload")}).status_code == 415


def test_form_mapping_endpoint(client, auth):
    client.put(f"{API}/profile", headers=auth, json={"father_name": "Rakesh Singh", "dob": "2007-03-10"})
    r = client.post(f"{API}/forms/map", headers=auth, json={"fields": [
        {"id": "f", "label": "Father's Name", "type": "text"}, {"id": "pw", "label": "Password", "type": "password"}]})
    m = {x["id"]: x for x in r.json()["mappings"]}
    assert m["f"]["value"] == "Rakesh Singh" and m["pw"]["skipped"]


def test_tracker_crud_and_upcoming(client, auth):
    from datetime import date, timedelta
    soon = (date.today() + timedelta(days=3)).isoformat()
    r = client.post(f"{API}/applications", headers=auth, json={"title": "Bank PO", "deadline": soon})
    aid = r.json()["id"]
    assert r.json()["days_left"] == 3
    assert [a["id"] for a in client.get(f"{API}/applications/upcoming", headers=auth).json()] == [aid]
    client.patch(f"{API}/applications/{aid}", headers=auth, json={"status": "submitted"})
    assert client.get(f"{API}/applications/upcoming", headers=auth).json() == []
    assert client.delete(f"{API}/applications/{aid}", headers=auth).status_code == 204


def test_bot_linking(client, auth):
    code = client.post(f"{API}/bot/link-code", headers=auth).json()["code"]
    assert client.post(f"{API}/bot/link", json={"code": code, "chat_id": "42"}, headers={"X-Bot-Secret": "wrong"}).status_code == 403
    ok = client.post(f"{API}/bot/link", json={"code": code, "chat_id": "42"}, headers={"X-Bot-Secret": "change-me-bot-secret"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    again = client.post(f"{API}/bot/link", json={"code": code, "chat_id": "43"}, headers={"X-Bot-Secret": "change-me-bot-secret"})
    assert again.status_code == 404  # one-time code


def test_unreadable_scan_gives_clear_error(client, auth):
    img = Image.new("RGB", (300, 300), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    r = client.post(f"{API}/notices", headers=auth, files={"file": ("scan.png", buf.getvalue(), "image/png")})
    assert r.status_code == 422 and "scanned" in r.json()["detail"].lower()
