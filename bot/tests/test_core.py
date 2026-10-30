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
            return httpx.Response(200, json={"filename": "photo_ready.jpg", "mime": "image/jpeg", "data_base64": base64.b64encode(b"READY").decode(),
                                             "report": {"ok": True, "warnings": [], "checks": [{"name": "Size in pixels", "ok": True, "detail": "200x230"}]}})
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
    replies = core.handle_image("1", PNG, "photo 3")
    assert "ready" in replies[0].text.lower() and replies[1].file == (b"READY", "photo_ready.jpg", "image/jpeg")


def test_image_without_caption_asks_which_notice(core):
    core.handle_text("1", "/link GOOD1234")
    reply = core.handle_image("1", PNG, "")[0].text
    assert "Which notice" in reply and "#4 Bank PO" in reply


def test_reminders_sent_once_per_day(core):
    core.handle_text("1", "/link GOOD1234")
    assert len(due_reminders(core.backend, core.store, 3)) == 1
    assert due_reminders(core.backend, core.store, 3) == []


def test_parse_telegram_updates():
    assert parse_update({"message": {"chat": {"id": 5}, "text": "hi"}}).text == "hi"
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


def test_whatsapp_payload_parsing():
    payload = {"entry": [{"changes": [{"value": {"messages": [{"from": "9198", "type": "text", "text": {"body": "hi"}}]}}]}]}
    assert extract_messages(payload)[0]["from"] == "9198"
    assert extract_messages({}) == []
