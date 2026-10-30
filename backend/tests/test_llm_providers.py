"""Checks the wire format of the model clients without any network (httpx MockTransport)."""

import json

import httpx
import pytest

from app.services import extraction
from app.services.llm.base import LLMError, LLMProvider
from app.services.llm.openai_compat import MetaProvider, OpenAICompatProvider


def _transport(handler):
    return httpx.MockTransport(handler)


def test_meta_provider_request_shape():
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "hello"}}]})

    p = MetaProvider("key123", transport=_transport(handler))
    assert p.chat([{"role": "user", "content": "hi"}], json_mode=True) == "hello"
    assert seen["url"] == "https://api.meta.ai/v1/chat/completions"
    assert seen["auth"] == "Bearer key123"
    assert seen["body"]["model"] == "muse-spark-1.3"
    assert seen["body"]["response_format"] == {"type": "json_object"}


def test_vision_message_uses_data_url():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{"message": {"content": "text"}}]})

    p = OpenAICompatProvider("https://example.test/v1", "k", "m", transport=_transport(handler))
    p.vision("read this", [(b"\x89PNGdata", "image/png")])
    parts = seen["body"]["messages"][0]["content"]
    assert parts[0]["type"] == "text" and parts[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_retries_then_raises(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(503)

    p = OpenAICompatProvider("https://example.test/v1", "k", "m", transport=_transport(handler))
    with pytest.raises(LLMError):
        p.chat([{"role": "user", "content": "x"}])
    assert calls["n"] == 3


def test_meta_requires_key():
    with pytest.raises(ValueError):
        MetaProvider("")


class FakeLLM(LLMProvider):
    name, offline = "fake", False

    def __init__(self, reply):
        self.reply = reply

    def chat(self, messages, **kw):
        return self.reply


def test_llm_extraction_fills_gaps_but_not_overrides(monkeypatch, sample_text):
    reply = json.dumps({"organisation": "Central Recruitment Board", "last_date": "2026-12-31", "fee": {"amount": 999, "currency": "INR"}, "gender": "female"})
    monkeypatch.setattr(extraction, "get_llm", lambda: FakeLLM(reply))
    out = extraction.extract_structured(sample_text)
    assert out["method"] == "rules+model"
    assert out["last_date"] == "2026-11-14"  # explicit rule match kept
    assert out["gender"] == "female"  # gap filled
    assert {r["field"] for r in out["needs_review"]} >= {"last_date", "fee"}


def test_bad_model_output_is_ignored(monkeypatch, sample_text):
    monkeypatch.setattr(extraction, "get_llm", lambda: FakeLLM("not json at all"))
    out = extraction.extract_structured(sample_text)
    assert out["last_date"] == "2026-11-14"


def test_llama_local_uses_ollama_defaults_and_vision_model():
    import json

    from app.services.llm.openai_compat import OllamaProvider

    seen = []

    def handler(request):
        seen.append((str(request.url), request.headers["authorization"], json.loads(request.content)["model"]))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    p = OllamaProvider(vision_model="llama3.2-vision", transport=_transport(handler))
    p.chat([{"role": "user", "content": "hi"}])
    p.vision("read", [(b"img", "image/png")])
    assert seen[0] == ("http://localhost:11434/v1/chat/completions", "Bearer ollama", "llama3.2")
    assert seen[1][2] == "llama3.2-vision"


def test_factory_selects_provider(monkeypatch):
    from app.core.config import get_settings
    from app.services.llm.factory import get_llm

    for kind, expected in (("mock", "mock"), ("llama_local", "llama_local"), ("meta", "meta")):
        monkeypatch.setenv("LLM_PROVIDER", kind)
        monkeypatch.setenv("META_API_KEY", "k")
        get_settings.cache_clear()
        get_llm.cache_clear()
        assert get_llm().name == expected
    get_settings.cache_clear()
    get_llm.cache_clear()
