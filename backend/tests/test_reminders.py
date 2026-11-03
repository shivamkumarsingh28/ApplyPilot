"""Deadline reminder windows: milestones 7/3/1, overdue, and the legacy window."""

from datetime import date, timedelta

API = "/api/v1"


def _app(client, auth, title: str, days_from_now: int, status: str = "planned") -> dict:
    deadline = (date.today() + timedelta(days=days_from_now)).isoformat()
    r = client.post(f"{API}/applications", headers=auth, json={"title": title, "deadline": deadline, "status": status})
    assert r.status_code == 201, r.text
    return r.json()


def test_upcoming_milestones_hit_exactly_7_3_1_and_overdue(client, auth):
    _app(client, auth, "in-7", 7)
    _app(client, auth, "in-3", 3)
    _app(client, auth, "in-1", 1)
    _app(client, auth, "in-2-not-a-milestone", 2)
    _app(client, auth, "in-14-not-yet", 14)
    overdue = _app(client, auth, "overdue-yesterday", -1)
    _app(client, auth, "submitted-in-3-ignored", 3, status="submitted")

    rows = client.get(f"{API}/applications/upcoming?milestones=7,3,1", headers=auth).json()
    titles = {r["title"] for r in rows}
    assert titles == {"in-7", "in-3", "in-1", "overdue-yesterday"}
    assert next(r for r in rows if r["id"] == overdue["id"])["days_left"] == -1


def test_upcoming_legacy_window_still_works(client, auth):
    _app(client, auth, "in-2", 2)
    _app(client, auth, "in-14", 14)
    rows = client.get(f"{API}/applications/upcoming?days=7", headers=auth).json()
    assert {r["title"] for r in rows} == {"in-2"}
