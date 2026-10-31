"""New real-world features: printable checklist, calendar export, summary + time saved."""

API = "/api/v1"


def _notice(client, auth, sample_text) -> int:
    client.put(f"{API}/profile", headers=auth,
               json={"full_name": "Asha Verma", "dob": "2007-03-10", "category": "obc",
                     "qualification": "10th", "percentage": 62, "gender": "male"})
    return client.post(f"{API}/notices", headers=auth, data={"text": sample_text}).json()["id"]


def test_checklist_is_printable_and_owner_only(client, auth, sample_text):
    nid = _notice(client, auth, sample_text)
    r = client.get(f"{API}/notices/{nid}/checklist", headers=auth)
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    body = r.text
    assert "Asha Verma" in body and "Eligibility" in body and "Missing" not in body  # heading is 'Still missing'
    assert "Class 10 certificate" in body and "window.print" in body
    other = client.post(f"{API}/auth/register", json={"email": "b@example.com", "password": "password123"}).json()["access_token"]
    assert client.get(f"{API}/notices/{nid}/checklist", headers={"Authorization": f"Bearer {other}"}).status_code == 404
    assert client.get(f"{API}/notices/{nid}/checklist").status_code == 401


def test_calendar_has_three_reminders_per_deadline(client, auth, sample_text):
    _notice(client, auth, sample_text)
    r = client.get(f"{API}/applications/calendar.ics", headers=auth)
    assert r.status_code == 200 and "text/calendar" in r.headers["content-type"]
    assert r.text.count("BEGIN:VEVENT") == 3
    assert "20261107T090000" in r.text and "20261113T090000" in r.text  # 14 Nov deadline, 7d and 1d before
    other = client.post(f"{API}/auth/register", json={"email": "c@example.com", "password": "password123"}).json()["access_token"]
    empty = client.get(f"{API}/applications/calendar.ics", headers={"Authorization": f"Bearer {other}"})
    assert empty.text.count("BEGIN:VEVENT") == 0


def test_summary_combines_counts_and_time_saved(client, auth, sample_text):
    _notice(client, auth, sample_text)
    r = client.get(f"{API}/applications/summary", headers=auth)
    assert r.status_code == 200
    s = r.json()
    assert s["total"] == 1 and s["open"] == 1 and s["next_deadline"] == "2026-11-14"
    assert s["next_days_left"] is not None and s["documents_ready"] == 0
    # A notice read + a tracker row is worth 35 saved minutes by the documented heuristic.
    assert s["time_saved_minutes"] == 35
    client.patch(f"{API}/applications/1", headers=auth, json={"status": "submitted"})
    s2 = client.get(f"{API}/applications/summary", headers=auth).json()
    assert s2["submitted"] == 1 and s2["open"] == 0


def test_scam_level_filter(client, auth, sample_text):
    _notice(client, auth, sample_text)
    ok = client.get(f"{API}/notices?scam_level=low", headers=auth)
    assert ok.status_code == 200 and len(ok.json()) == 1
    none = client.get(f"{API}/notices?scam_level=high", headers=auth)
    assert none.json() == []
