"""Tool Calling Inventory: framework behaviours + P1/P2 tools + agent wiring."""

from app.services.agents.tools import TOOLS, call_tool


def _notice(client, auth, sample_text):
    r = client.post("/api/v1/notices", data={"text": sample_text}, headers=auth)
    assert r.status_code == 201, r.text
    return r.json()


def test_tool_registry_is_large_and_well_formed():
    assert len(TOOLS) >= 40
    for t in TOOLS.values():
        assert t.description and isinstance(t.params, dict)
        assert t.kind in ("read", "compute", "write", "destructive", "external")
    write_kinds = [t.name for t in TOOLS.values() if t.kind in ("write", "destructive")]
    assert write_kinds, "write tools must declare their kind"


def test_needs_input_is_an_answer_not_an_error(db_ctx):
    out, rec = call_tool("get_notice_page", {"page": "x"}, db_ctx, {"get_notice_page"})
    assert "error" in out  # no notices yet -> ToolError path is fine too
    out, rec = call_tool("parse_date_text", {}, db_ctx, {"parse_date_text"})
    assert rec.ok and out["needs_input"] == ["text"]
    from app.services.agents.runner import render

    assert "Tell me" in render("parse_date_text", out)


def _notice_as_ctx_user(db_ctx, client, auth, sample_text):
    """_notice() via HTTP creates the notice for `auth`'s user; re-point the ctx user so tools can see it."""
    from app.db.models import User

    n = _notice(client, auth, sample_text)
    owner = db_ctx.db.query(User).filter(User.email == "a@example.com").first()
    from app.services.agents.tools import ToolContext

    return n, ToolContext(db=db_ctx.db, user=owner)


def test_two_step_confirmation_blocks_the_write(db_ctx, client, auth, sample_text):
    n, ctx = _notice_as_ctx_user(db_ctx, client, auth, sample_text)
    from app.db.models import Application

    before = ctx.db.query(Application).filter_by(user_id=ctx.user.id).count()
    out, rec = call_tool("create_application", {"notice_id": n["id"]}, ctx, {"create_application"})
    assert out.get("confirmation_required") is True and "Nothing has been changed yet" in out["proposal"]
    assert ctx.db.query(Application).filter_by(user_id=ctx.user.id).count() == before  # the proposal changed nothing
    out, rec = call_tool("create_application", {"notice_id": n["id"], "confirm": True}, ctx, {"create_application"})
    assert "application_id" in out  # runs (or reports already tracking) only after confirmation


def test_parse_date_and_calculators(db_ctx):
    out, _ = call_tool("parse_date_text", {"text": "10 March 2007"}, db_ctx, {"parse_date_text"})
    assert out["iso"] == "2007-03-10" and "2007-03-10" in out["working"]
    out, _ = call_tool("convert_grade", {"cgpa": 8.0}, db_ctx, {"convert_grade"})
    assert out["percentage"] == 76.0


def test_notice_reading_tools(db_ctx, client, auth, sample_text):
    n, ctx = _notice_as_ctx_user(db_ctx, client, auth, sample_text)
    out, _ = call_tool("get_key_answers", {"notice_id": n["id"]}, ctx, {"get_key_answers"})
    assert any("Last date" in a for a in out["answers"])
    out, _ = call_tool("get_notice_page", {"notice_id": n["id"], "page": 1}, ctx, {"get_notice_page"})
    assert "SAMPLE" in out["text"] and out["of_pages"] >= 3
    out, _ = call_tool("explain_eligibility_rule", {"notice_id": n["id"], "rule": "age"}, ctx, {"explain_eligibility_rule"})
    assert out["value"]["min"] == 17.5
    out, _ = call_tool("find_in_notice", {"notice_id": n["id"], "words": "physical fitness test"}, ctx, {"find_in_notice"})
    assert out["matches"] and out["matches"][0]["page"] == 3


def test_what_if_does_not_save(db_ctx, client, auth, sample_text):
    from app.services.profile_store import load_profile

    n, _ctx = _notice_as_ctx_user(db_ctx, client, auth, sample_text)
    before = load_profile(_ctx.db, _ctx.user).get("category")
    out, _ = call_tool("what_if_eligibility", {"notice_id": n["id"], "change": {"category": "sc", "dob": "2007-03-10",
                                                                                  "qualification": "10th", "percentage": 62}},
                       _ctx, {"what_if_eligibility"})
    assert out["saved_profile_unchanged"] is True and out["changed"]["category"] == "sc"
    assert load_profile(_ctx.db, _ctx.user).get("category") == before


def test_foreign_notice_is_invisible_to_tools(db_ctx, client, auth, sample_text):
    n = _notice(client, auth, sample_text)
    client.post("/api/v1/auth/register", json={"email": "z@example.com", "password": "password123"})
    from app.db import session as sm
    from app.db.models import User
    from app.services.agents.tools import ToolContext

    db = next(sm.get_db())
    other = ToolContext(db=db, user=db.query(User).filter(User.email == "z@example.com").first())
    out, rec = call_tool("get_notice_page", {"notice_id": n["id"], "page": 1}, other, {"get_notice_page"})
    assert not rec.ok and out["error"] == "Notice not found"  # same as missing: nothing leaks
    db.close()


def test_every_agent_sees_a_short_list_and_tools_exist():
    from app.services.agents.agents import AGENTS

    for a in AGENTS.values():
        assert len(a.tools) <= 12, (a.name, len(a.tools))
        missing = [t for t in a.tools if t not in TOOLS]
        assert not missing, (a.name, missing)


def test_tool_choice_offline_keywords():
    from app.services.agents.supervisor import keyword_route

    cases = {
        "am I eligible for this notice": "eligibility_agent",
        "what is the fee and last date": "notice_agent",
        "my photo is blurry, is it ok": "photo_agent",
        "list my vault documents": "documents_agent",
        "which notice should I apply first": "tracker_agent",
        "show my profile details": "profile_agent",
    }
    hits = sum(1 for msg, want in cases.items() if keyword_route(msg).agent == want)
    assert hits >= 5, cases


def test_update_profile_field_validates_and_saves(db_ctx):
    out, rec = call_tool("update_profile_field", {"field": "dob", "value": "10 March 2007"}, db_ctx, {"update_profile_field"})
    assert out.get("confirmation_required") is True  # write tool: proposal first
    out, rec = call_tool("update_profile_field", {"field": "dob", "value": "2007-03-10", "confirm": True},
                         db_ctx, {"update_profile_field"})
    assert rec.ok and out["value"] == "2007-03-10"
    out, rec = call_tool("update_profile_field", {"field": "dob", "value": "not a date", "confirm": True},
                         db_ctx, {"update_profile_field"})
    assert not rec.ok and "error" in out
