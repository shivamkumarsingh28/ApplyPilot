import base64
import io
import time

from PIL import Image


def _notice(client, auth, sample_text):
    r = client.post("/api/v1/notices", data={"text": sample_text}, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()


def test_background_job_ingest(client, auth, sample_text):
    r = client.post("/api/v1/jobs/ingest", files={"file": ("n.txt", sample_text.encode(), "text/plain")}, headers=auth)
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    job = None
    for _ in range(100):
        job = client.get(f"/api/v1/jobs/{job_id}", headers=auth).json()
        if job["status"] in ("ready", "failed"):
            break
        time.sleep(0.05)
    assert job["status"] == "ready", job
    assert job["notice_id"] and "Last date" in " ".join(job["summary"])
    assert job["timings"].get("index_s") is not None
    # Chat-created notice shows up in the same web list (plan 4.3)
    assert any(n["id"] == job["notice_id"] for n in client.get("/api/v1/notices", headers=auth).json())


def test_answer_cache_and_paraphrase(client, auth, sample_text):
    n = _notice(client, auth, sample_text)
    a1 = client.post(f"/api/v1/notices/{n['id']}/ask", json={"question": "What is the cost to apply?"}, headers=auth).json()
    assert "250" in a1["answer"], a1
    a2 = client.post(f"/api/v1/notices/{n['id']}/ask", json={"question": "What is the cost to apply?"}, headers=auth).json()
    assert a2["answer"] == a1["answer"]


def test_evaluation_set_scores(client, auth, sample_text):
    from app.services.evaluation import evaluate_retrieval

    n = _notice(client, auth, sample_text)
    from app.db import session as sm
    from app.db.models import Notice

    db = next(sm.get_db())
    result = evaluate_retrieval(db, db.get(Notice, n["id"]))
    db.close()
    assert result["total"] == 30
    assert result["score"] >= 0.8, result


def test_colours_any_name_and_hex():
    from app.services.colours import parse_colour, resolve_background

    assert parse_colour("light blue") == ((173, 216, 230), "light blue")
    assert parse_colour("#e6f0ff")[0] == (230, 240, 255)
    assert parse_colour("not-a-colour") is None
    rgb, label, overridden = resolve_background("light blue", "white")
    assert overridden and label == "white"  # portal rule wins (plan 4.2)


def test_photo_custom_colour(client, auth):
    from tests.conftest import make_jpeg

    r = client.post("/api/v1/photo/process", files={"file": ("p.jpg", make_jpeg(), "image/jpeg")},
                    data={"kind": "photo", "background": "#e6f0ff"}, headers=auth)
    assert r.status_code == 200, r.text
    img = Image.open(io.BytesIO(base64.b64decode(r.json()["data_base64"])))
    assert img.size == (413, 531)


def test_vault_copy_and_delete_rules(client, auth):
    up = client.post("/api/v1/documents", files={"file": ("cert.txt", b"certificate bytes", "text/plain")},
                     data={"kind": "marksheet_10"}, headers=auth)
    assert up.status_code == 201, up.text
    doc = up.json()
    copy = client.post(f"/api/v1/documents/{doc['id']}/copy", headers=auth)
    # copy without notice/application is allowed and has empty ref
    assert copy.status_code == 201, copy.text
    assert copy.json()["is_original"] is False and copy.json()["original_id"] == doc["id"]
    blocked = client.delete(f"/api/v1/documents/{doc['id']}", headers=auth)
    assert blocked.status_code == 409 and "APP" in blocked.text or blocked.status_code == 409
    assert client.delete(f"/api/v1/documents/{copy.json()['id']}", headers=auth).status_code == 204
    assert client.get("/api/v1/documents", headers=auth).json()[0]["id"] == doc["id"]  # original untouched
    assert client.delete(f"/api/v1/documents/{doc['id']}", headers=auth).status_code == 204


def test_oauth_providers_listed_when_unconfigured(client):
    r = client.get("/api/v1/auth/providers")
    assert r.json() == {"providers": [], "email_password": True}
    assert client.get("/api/v1/auth/oauth/google/start").status_code == 404


def test_search_unconfigured_is_clear(client, auth, monkeypatch):
    # Force the unconfigured state: the developer's real .env may have a provider set.
    from app.core.config import get_settings

    monkeypatch.setenv("SEARCH_PROVIDER", "")
    monkeypatch.setenv("BRAVE_API_KEY", "")
    monkeypatch.setenv("TAVILY_API_KEY", "")
    get_settings.cache_clear()
    try:
        r = client.get("/api/v1/search", params={"q": "army jobs"}, headers=auth)
        assert r.status_code == 503
        r2 = client.post("/api/v1/search/save", json={"url": "https://evil.example.com/x.pdf"}, headers=auth)
        assert r2.status_code == 422  # allowlist blocks untrusted domains before any download
    finally:
        get_settings.cache_clear()
