"""Regression tests for delete flows that crashed on Postgres foreign keys.

The notice delete used to 500 when an ingest job (or answer-cache / vault copy)
still referenced the notice; the application delete did the same when a vault
copy had been made for it. These exercise exactly those paths end to end.
"""

API = "/api/v1"


def _notice(client, auth, sample_text):
    r = client.post(f"{API}/notices", headers=auth, data={"text": sample_text})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_delete_notice_after_ask_and_tracker(client, auth, sample_text):
    nid = _notice(client, auth, sample_text)
    # Ask creates an answer-cache row referencing the notice.
    r = client.post(f"{API}/notices/{nid}/ask", headers=auth, json={"question": "What is the last date?"})
    assert r.status_code == 200, r.text
    # Creating the notice also created a tracker application referencing it.
    apps = client.get(f"{API}/applications", headers=auth).json()
    assert any(a["notice_id"] == nid for a in apps)

    assert client.delete(f"{API}/notices/{nid}", headers=auth).status_code == 204
    assert client.get(f"{API}/notices/{nid}", headers=auth).status_code == 404
    assert client.get(f"{API}/notices", headers=auth).json() == []
    # The application survives, now unlinked from the deleted notice.
    apps = client.get(f"{API}/applications", headers=auth).json()
    assert apps and all(a["notice_id"] is None for a in apps)


def test_delete_notice_with_ingest_job_reference(client, auth, sample_text, db_ctx):
    from app.db.models import IngestJob

    nid = _notice(client, auth, sample_text)
    db_ctx.db.add(IngestJob(user_id=db_ctx.user.id, notice_id=nid, status="ready"))
    db_ctx.db.commit()

    assert client.delete(f"{API}/notices/{nid}", headers=auth).status_code == 204
    assert client.get(f"{API}/notices", headers=auth).json() == []


def test_delete_application_with_vault_copy(client, auth, sample_text):
    nid = _notice(client, auth, sample_text)
    doc = client.post(f"{API}/documents", headers=auth, data={"kind": "degree"},
                      files={"file": ("degree.txt", b"degree certificate", "text/plain")}).json()
    # Copying with a notice creates/links an application and a copy referencing it.
    copy = client.post(f"{API}/documents/{doc['id']}/copy?notice_id={nid}", headers=auth)
    assert copy.status_code == 201, copy.text
    app_id = copy.json()["application_id"]
    assert app_id

    assert client.delete(f"{API}/applications/{app_id}", headers=auth).status_code == 204
    assert all(a["id"] != app_id for a in client.get(f"{API}/applications", headers=auth).json())
    # The vault copy survives, unlinked.
    docs = client.get(f"{API}/documents", headers=auth).json()
    assert any(d["id"] == copy.json()["id"] and d["application_id"] is None for d in docs)


def test_delete_original_with_copies_needs_force(client, auth, sample_text):
    nid = _notice(client, auth, sample_text)
    doc = client.post(f"{API}/documents", headers=auth, data={"kind": "degree"},
                      files={"file": ("degree.txt", b"degree certificate", "text/plain")}).json()
    assert client.post(f"{API}/documents/{doc['id']}/copy?notice_id={nid}", headers=auth).status_code == 201
    assert client.delete(f"{API}/documents/{doc['id']}", headers=auth).status_code == 409
    assert client.delete(f"{API}/documents/{doc['id']}?force=true", headers=auth).status_code == 204
    assert client.get(f"{API}/documents", headers=auth).json() == []


def test_delete_account_removes_everything(client, auth, sample_text):
    _notice(client, auth, sample_text)
    client.post(f"{API}/documents", headers=auth, data={"kind": "other"},
                files={"file": ("note.txt", b"personal note", "text/plain")})
    assert client.delete(f"{API}/auth/me", headers=auth).status_code == 204
    # Old token no longer works and the email can be registered again.
    assert client.get(f"{API}/profile", headers=auth).status_code == 401
    r = client.post(f"{API}/auth/register", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 201, r.text
