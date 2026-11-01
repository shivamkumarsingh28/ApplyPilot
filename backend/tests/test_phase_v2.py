"""Phase V2: Meta default, structure-aware chunking, generic extraction,
calculator tools, whole-notice verification, shared-notice dedupe."""

import json

from app.services.llm.base import LLMProvider


class FakeLLM(LLMProvider):
    name, offline = "fake", False

    def __init__(self, reply):
        self.reply = reply

    def chat(self, messages, **kw):
        return self.reply(messages) if callable(self.reply) else self.reply


def _auth2(client):
    r = client.post("/api/v1/auth/register", json={"email": "b@example.com", "password": "password123", "full_name": "Bala Rao"})
    assert r.status_code == 201, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_meta_is_default_and_missing_key_falls_back(monkeypatch):
    from app.core.config import Settings

    monkeypatch.setattr(Settings, "model_config", dict(Settings.model_config, env_file=None))
    s = Settings()
    assert s.llm_provider == "meta" and s.meta_model == "muse-spark-1.3"

    from app.core.config import get_settings
    from app.services.llm.factory import get_llm

    monkeypatch.setenv("LLM_PROVIDER", "meta")
    monkeypatch.setenv("META_API_KEY", "")
    get_settings.cache_clear()
    get_llm.cache_clear()
    try:
        assert get_llm().name == "mock"  # no key: offline mock, never a crash
        monkeypatch.setenv("META_API_KEY", "k")
        get_settings.cache_clear()
        get_llm.cache_clear()
        assert get_llm().name == "meta"
    finally:
        get_settings.cache_clear()
        get_llm.cache_clear()


def test_chunking_keeps_heading_and_table_rows():
    from app.services.chunking import chunk_pages

    pages = ["Important Dates\nStarting date of application is 01 October 2026.\nLast date is 14 November 2026.",
             "Application Fee\nGeneral category Rs. 250\nOBC category Rs. 100\nSC category Rs. 0"]
    chunks = chunk_pages(pages)
    fee = [c for c in chunks if "250" in c["text"]]
    assert fee and fee[0]["page"] == 2
    assert all("page" in c and "heading" in c and "parent" in c for c in chunks)
    dates = [c for c in chunks if "14 November" in c["text"]]
    assert dates and "Important" in dates[0]["heading"]


def test_extraction_is_generic_not_job_only():
    from app.services.extraction import rule_extract

    s = rule_extract("National Scholarship Portal 2026\nScholarship for students. Last date is 31 December 2026. "
                     "Apply at https://scholarships.gov.in/apply\nMinimum 60% marks in Class 12.")
    assert s["doc_type"] == "scholarship" and s["kind"] == "scholarship"
    assert s["last_date"] == "2026-12-31"
    assert s["apply_link"] == "https://scholarships.gov.in/apply"
    assert s["evidence"]["last_date"]["page"] == 1

    from pathlib import Path

    sample = rule_extract((Path(__file__).resolve().parents[2] / "samples" / "sample_notice.txt").read_text().replace("\\f", "\f"))
    assert sample["kind"] == "government_job"
    assert sample["last_date"] == "2026-11-14"
    assert sample["apply_link"] and "sampledefence.gov.in" in sample["apply_link"]
    assert sample["gender"] is None  # no gender restriction in the sample


def test_calculators_are_exact():
    from datetime import date

    from app.services import calculators

    assert calculators.calc_age(date(2007, 3, 10), date(2026, 10, 1))["years"] == 19
    assert calculators.calc_days_left(date(2026, 11, 14), date(2026, 11, 1))["days_left"] == 13
    assert calculators.calc_max_age_with_relaxation(21, {"obc": 2}, "OBC")["effective_max_age"] == 23
    assert calculators.calc_fee_total([250, 100])["total"] == 350
    assert calculators.calc_percentage(270, 600)["percentage"] == 45.0


def test_calculator_tools_via_agent(db_ctx):
    from app.services.agents.tools import call_tool

    out, rec = call_tool("calc_age", {"dob": "2007-03-10", "as_of": "2026-10-01"}, db_ctx,
                         {"calc_age"})
    assert rec.ok and out["years"] == 19 and "19 years" in out["working"]
    out, rec = call_tool("calc_percentage", {"obtained": 270, "maximum": 600}, db_ctx, {"calc_percentage"})
    assert rec.ok and out["percentage"] == 45.0
    out, rec = call_tool("calc_age", {"dob": "not-a-date"}, db_ctx, {"calc_age"})
    assert not rec.ok and "error" in out  # teaching error, not a crash


def test_shared_notice_second_user_is_linked_not_reprocessed(client, auth, sample_text):
    n1 = client.post("/api/v1/notices", data={"text": sample_text}, headers=auth).json()
    auth2 = _auth2(client)
    # Same text again (e.g. the same PDF re-uploaded by someone else) -> same notice id.
    n2 = client.post("/api/v1/notices", data={"text": sample_text}, headers=auth2).json()
    assert n2["id"] == n1["id"] and n2["shared"] is True
    assert client.get("/api/v1/notices", headers=auth2).json()[0]["id"] == n1["id"]
    a = client.post(f"/api/v1/notices/{n1['id']}/ask", json={"question": "What is the fee?"}, headers=auth2).json()
    assert "250" in a["answer"]
    elig = client.get(f"/api/v1/notices/{n1['id']}/eligibility", headers=auth2)
    assert elig.status_code == 200  # own profile, shared notice
    # Linked user deleting removes only their link; the owner keeps the notice.
    assert client.delete(f"/api/v1/notices/{n1['id']}", headers=auth2).status_code == 204
    assert client.get(f"/api/v1/notices/{n1['id']}", headers=auth).status_code == 200
    assert client.get(f"/api/v1/notices/{n1['id']}", headers=auth2).status_code == 404


def test_personal_document_is_never_shared(client, auth):
    personal = ("Asha Verma Marksheet Statement of Marks Class 10 Board Examination 2026. "
                "Roll number 12345. Total marks obtained 540 out of 600 in the examination.")
    n1 = client.post("/api/v1/notices", data={"text": personal}, headers=auth).json()
    auth2 = _auth2(client)
    n2 = client.post("/api/v1/notices", data={"text": personal}, headers=auth2).json()
    # Personal-looking uploads stay private: a second copy, a 404 for the other user.
    assert n2["id"] != n1["id"] or n2["shared"] is False
    assert client.get(f"/api/v1/notices/{n1['id']}", headers=auth2).status_code == 404


def test_whole_notice_answer_and_hallucinated_number_rejected(client, auth, sample_text, monkeypatch):
    from app.services import rag

    n = client.post("/api/v1/notices", data={"text": sample_text}, headers=auth).json()
    monkeypatch.setattr(rag, "get_llm", lambda: FakeLLM("The application fee is Rs. 250 (page 2)."))
    ok = client.post(f"/api/v1/notices/{n['id']}/ask", json={"question": "What is the fee?"}, headers=auth).json()
    assert "250" in ok["answer"] and ok["mode"] == "whole_notice"

    monkeypatch.setattr(rag, "get_llm", lambda: FakeLLM("The application fee is Rs. 999 (page 2)."))
    bad = client.post(f"/api/v1/notices/{n['id']}/ask", json={"question": "What is the fee exactly?"}, headers=auth).json()
    assert "999" not in bad["answer"] and bad["mode"] == "not_found"


def test_notice_out_exposes_apply_link(client, auth, sample_text):
    n = client.post("/api/v1/notices", data={"text": sample_text}, headers=auth).json()
    assert n["apply_link"] and "sampledefence.gov.in" in n["apply_link"]
    assert n["doc_type"] == "government_job"
    assert "Apply here" in " ".join(__import__("app.services.key_answers", fromlist=["key_answers"]).key_answers(n["structured"]))
    assert json.dumps(n)  # serialisable
