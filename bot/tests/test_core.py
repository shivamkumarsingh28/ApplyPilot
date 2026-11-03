import base64
import hashlib
import hmac
import json

import httpx
import pytest

from applypilot_bot.api_client import Backend
from applypilot_bot.core import BotCore
from applypilot_bot.reminders import due_reminders
from applypilot_bot.store import Store
from applypilot_bot.transports.telegram import parse_update
from applypilot_bot.transports.whatsapp import extract_messages, valid_signature

PNG = b"fakeimagebytes"


def fake_backend(calls):
    def handler(request: httpx.Request):
        path = request.url.path.replace("/api/v1", "")
        calls.append((request.method, path, request.headers.get("authorization")))
        if path == "/bot/link":
            body = json.loads(request.content)
            if body["code"] != "GOOD1234" or request.headers.get("x-bot-secret") != "s3cret":
                return httpx.Response(404, json={"detail": "Code not found or already used"})
            return httpx.Response(200, json={"access_token": "tok-123"})
        if request.headers.get("authorization") != "Bearer tok-123":
            return httpx.Response(401, json={"detail": "Invalid or expired token"})
        if path == "/assistant/chat":
            return httpx.Response(200, json={"answer": "The last date is 14 November 2026."})
        if path == "/applications/upcoming":
            return httpx.Response(200, json=[{"id": 7, "title": "Army post", "deadline": "2026-11-14", "days_left": 2}])
        if path == "/notices":
            return httpx.Response(200, json=[{"id": 3, "title": "Army post"}, {"id": 4, "title": "Bank PO"}])
        if path == "/photo/process":
            body = request.content.decode(errors="ignore")
            calls.append(("PHOTO_BODY", body, None))
            return httpx.Response(200, json={"filename": "photo_ready.jpg", "mime": "image/jpeg", "data_base64": base64.b64encode(b"READY").decode(),
                                             "report": {"ok": True, "warnings": [], "checks": [{"name": "Size in pixels", "ok": True, "detail": "200x230"}]}})
        if path == "/documents":
            return httpx.Response(201, json={"id": 5, "filename": "saved.pdf"})
        if path == "/pdf/compress":
            return httpx.Response(200, json={"filename": "doc_compressed.pdf", "mime": "application/pdf",
                                             "data_base64": base64.b64encode(b"SMALLPDF").decode(),
                                             "report": {"original_kb": 900.0, "final_kb": 180.0, "pages": 4, "within": True, "method": "images resized"}})
        if path == "/jobs/ingest":
            return httpx.Response(202, json={"job_id": 9, "status": "queued"})
        if path == "/jobs/9":
            return httpx.Response(200, json={"id": 9, "status": "ready", "notice_id": 3, "title": "Army post",
                                             "summary": ["Last date: 2026-11-14"], "timings": {}, "error": ""})
        if path == "/profile":
            if request.method == "PUT":
                return httpx.Response(200, json={"dob": json.loads(request.content).get("dob")})
            return httpx.Response(200, json={"full_name": "Asha"})
        if path == "/notices/3/eligibility":
            return httpx.Response(200, json={"verdict": "needs_info", "checks": [], "missing_profile_fields": ["dob"]})
        if path == "/notices/4/eligibility":
            return httpx.Response(200, json={"verdict": "eligible", "checks": [{"rule": "Age", "detail": "20 years on 2026-10-01"}], "missing_profile_fields": []})
        return httpx.Response(404, json={"detail": "nope"})

    return handler


@pytest.fixture()
def core():
    calls = []
    backend = Backend("http://backend", "s3cret", transport=httpx.MockTransport(fake_backend(calls)))
    c = BotCore(backend, Store(":memory:"))
    c.calls = calls
    return c


def test_unlinked_chat_is_told_how_to_link(core):
    assert "Create link code" in core.handle_text("1", "what is the last date?")[0].text
    assert core.calls == []  # nothing is sent to the backend without a link


def test_link_flow_and_question(core):
    assert "Could not link" in core.handle_text("1", "/link WRONG")[0].text
    assert "Linked" in core.handle_text("1", "/link good1234")[0].text
    assert "14 November" in core.handle_text("1", "When is the last date?")[0].text
    assert core.calls[-1][2] == "Bearer tok-123"


def test_deadlines_command(core):
    core.handle_text("1", "/link GOOD1234")
    assert "Army post: 2026-11-14 (2 days left)" in core.handle_text("1", "/deadlines")[0].text


def test_expired_token_unlinks(core):
    core.store.link("9", "old-token")
    reply = core.handle_text("9", "hello there")[0].text
    assert "session ended" in reply and core.store.token("9") is None


def test_image_with_caption_returns_file(core):
    core.handle_text("1", "/link GOOD1234")
    replies = core.handle_image("1", PNG, "photo 3 light blue")
    assert "preview" in replies[0].text.lower() and replies[1].file == (b"READY", "photo_ready.jpg", "image/jpeg")
    confirm = core.handle_text("1", "yes")
    assert "saved to your vault" in confirm[0].text.lower() and confirm[1].file[0] == b"READY"


def test_document_ingest_flow(core):
    core.handle_text("1", "/link GOOD1234")
    ack = core.handle_document("1", b"%PDF-fake", "notice.pdf", "application/pdf")
    assert "reading your notice" in ack[0].text
    done = core.poll_job("1")
    assert "ready" in done[0].text and "Last date" in done[0].text
    assert core.store.get_state("1", "notice_id") == "3"
    big = core.handle_document("1", b"x" * (5 * 1024 * 1024 + 1), "big.pdf", "application/pdf")
    assert "5 MB" in big[0].text


def test_dob_prompt_and_save(core):
    core.handle_text("1", "/link GOOD1234")
    core.store.set_state("1", "notice_id", "3")
    ask = core.handle_text("1", "/eligible")
    assert "date of birth" in ask[0].text.lower()
    saved = core.handle_text("1", "05/08/2004")
    assert "saved" in saved[0].text.lower()
    assert core.store.get_state("1", "awaiting_dob") is None


def test_split_text():
    from applypilot_bot.core import split_text

    parts = split_text("A. " * 400)
    assert len(parts) > 1 and all(len(p) <= 1100 for p in parts)


def test_image_without_caption_resizes_without_asking(core):
    # New default: a bare photo is resized only, never blocked asking which
    # notice, and never background-changed. Portal mode still asks.
    core.handle_text("1", "/link GOOD1234")
    reply = core.handle_image("1", PNG, "")[0].text
    assert "Background NOT changed" in reply
    portal = core.handle_image("1", PNG, "photo")[0].text
    assert "Which notice" in portal and "#4 Bank PO" in portal


def test_reminders_sent_once_per_day(core):
    core.handle_text("1", "/link GOOD1234")
    assert len(due_reminders(core.backend, core.store, 3)) == 1
    assert due_reminders(core.backend, core.store, 3) == []


def test_parse_telegram_updates():
    assert parse_update({"message": {"chat": {"id": 5}, "text": "hi"}}).text == "hi"
    pdf = parse_update({"message": {"chat": {"id": 5}, "document": {"file_id": "d1", "file_name": "n.pdf", "mime_type": "application/pdf"}}})
    assert pdf.is_document and pdf.filename == "n.pdf"
    photo = parse_update({"message": {"chat": {"id": 5}, "photo": [{"file_id": "small"}, {"file_id": "big"}], "caption": "photo 3"}})
    assert photo.file_id == "big" and photo.caption == "photo 3"
    assert parse_update({"message": {"chat": {"id": 5}, "sticker": {}}}) is None
    assert parse_update({"edited_message": {}}) is None


def test_whatsapp_signature_check():
    body = b'{"entry": []}'
    good = "sha256=" + hmac.new(b"appsecret", body, hashlib.sha256).hexdigest()
    assert valid_signature("appsecret", body, good)
    assert not valid_signature("appsecret", body, "sha256=deadbeef")
    assert not valid_signature("", body, good)
    assert not valid_signature("appsecret", body, "")


def test_image_intent_defaults_to_resize_only():
    from applypilot_bot.core import parse_image_intent

    plain = parse_image_intent("")
    assert plain.kind == "photo_resize" and plain.change_background is False
    assert plain.background is None and plain.width is None
    sized = parse_image_intent("resize 200x230 compress 50kb")
    assert (sized.width, sized.height, sized.max_kb) == (200, 230, 50)
    assert sized.kind == "photo_resize" and sized.change_background is False
    # Classic form still works, but now it is the ONLY way the background changes.
    portal = parse_image_intent("photo 3 light blue")
    assert portal.kind == "photo" and portal.notice_id == 3 and portal.change_background is True
    explicit = parse_image_intent("resize 200x230 blue background")
    assert explicit.change_background is True and explicit.background == "blue"
    bare = parse_image_intent("photo 3")
    assert bare.notice_id == 3 and bare.change_background is False


def test_bot_photo_defaults_keep_background(core):
    core.handle_text("1", "/link GOOD1234")
    core.handle_image("1", PNG, "resize 200x230")
    body = [c[1] for c in core.calls if c[0] == "PHOTO_BODY"][-1]
    assert 'name="kind"' in body and "photo_resize" in body
    assert "change_background" in body and "false" in body
    assert 'name="width"' in body and "200" in body


def test_document_intent_routing(core):
    from applypilot_bot.core import parse_document_intent

    assert parse_document_intent("", "n.pdf", "application/pdf").action == "notice"
    assert parse_document_intent("save", "n.pdf", "application/pdf").action == "save"
    assert parse_document_intent("compress 500kb", "n.pdf", "application/pdf").max_kb == 500
    assert parse_document_intent("", "cert.jpg", "image/jpeg").action == "save"

    core.handle_text("1", "/link GOOD1234")
    saved = core.handle_document("1", b"%PDF-fake", "cert.pdf", "application/pdf", "save to vault")
    assert "did not read it as a notice" in saved[0].text
    shrunk = core.handle_document("1", b"%PDF-fake", "big.pdf", "application/pdf", "compress 200kb")
    assert "900.0 KB" in shrunk[0].text and shrunk[1].file[0] == b"SMALLPDF"


def test_whatsapp_payload_parsing():
    payload = {"entry": [{"changes": [{"value": {"messages": [{"from": "9198", "type": "text", "text": {"body": "hi"}}]}}]}]}
    assert extract_messages(payload)[0]["from"] == "9198"
    assert extract_messages({}) == []
