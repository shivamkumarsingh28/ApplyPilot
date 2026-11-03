"""HTTP client for OpenAI-compatible chat APIs.

Meta Model API (https://api.meta.ai/v1) exposes /chat/completions with Bearer
auth, and the open-weights hosts (Baseten, Fireworks, Modal, vLLM) do too, so one
small client covers all three. Meta-specific defaults live in `MetaProvider`.
"""

from __future__ import annotations

import json
import logging
import time

import httpx

from app.services.llm.base import LLMError, LLMProvider

log = logging.getLogger(__name__)


class OpenAICompatProvider(LLMProvider):
    name = "openai_compat"

    def __init__(self, base_url: str, api_key: str, model: str, *, timeout: float = 90.0, extra_body: dict | None = None,
                 embedding_model: str = "", vision_model: str = "", transport: httpx.BaseTransport | None = None):
        if not base_url or not (model or embedding_model):
            raise ValueError("base_url and a chat or embedding model are required")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.embedding_model = embedding_model
        self.vision_model = vision_model
        self.extra_body = extra_body or {}
        self._client = httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            transport=transport,
        )

    def _post(self, path: str, payload: dict, retries: int = 2) -> dict:
        last: Exception | None = None
        for attempt in range(retries + 1):
            try:
                resp = self._client.post(f"{self.base_url}{path}", json=payload)
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                if resp.status_code >= 400:
                    # Surface the provider's own message (e.g. invalid_api_key) — retrying
                    # a 401 never helps, and hiding it once produced blank answers.
                    detail = ""
                    try:
                        detail = str(resp.json().get("error", {}).get("message") or resp.text[:200])
                    except ValueError:
                        detail = resp.text[:200]
                    raise LLMError(f"model API error {resp.status_code}: {detail}")
                return resp.json()
            except LLMError:
                raise
            except (httpx.HTTPError, ValueError) as exc:  # network or bad JSON
                last = exc
                log.warning("LLM call failed (attempt %s): %s", attempt + 1, exc)
                if attempt < retries:
                    time.sleep(1.0 * (attempt + 1))
        raise LLMError(f"model call failed: {last}")

    def chat(self, messages, *, json_mode=False, temperature=0.2, max_tokens=1500, model: str | None = None) -> str:
        payload = {"model": model or self.model, "messages": messages, "temperature": temperature,
                   "max_tokens": max_tokens, **self.extra_body}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        data = self._post("/chat/completions", payload)
        if isinstance(data, dict) and data.get("error"):
            raise LLMError(f"model API error: {data['error']}")
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"unexpected response shape: {exc}") from exc
        if content is None or (isinstance(content, str) and not content.strip()):
            # An empty success body is a failure, not an answer. Callers fall back
            # to extractive answers instead of showing (and caching) a blank.
            raise LLMError("model returned an empty response")
        return content

    def chat_with_tools(self, messages, tools):
        """Native function calling (Meta/OpenAI-compatible). Parallel calls supported."""
        specs = []
        for t in tools:
            props = {k: {"type": "string", "description": v} for k, v in (t.get("params") or {}).items()}
            specs.append({"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                           "parameters": {"type": "object", "properties": props}}})
        data = self._post("/chat/completions", {"model": self.model, "messages": messages, "tools": specs,
                                                "temperature": 0.0, "max_tokens": 800})
        try:
            msg = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"unexpected response shape: {exc}") from exc
        calls = []
        for c in msg.get("tool_calls") or []:
            fn = c.get("function") or {}
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except ValueError:
                args = {}
            if fn.get("name"):
                calls.append({"name": fn["name"], "args": args if isinstance(args, dict) else {}})
        return {"calls": calls, "text": (msg.get("content") or None)}

    def vision(self, prompt, images, *, json_mode=False) -> str:
        """Use the dedicated vision model when one is configured (small local models are text-only)."""
        if not self.vision_model:
            return super().vision(prompt, images, json_mode=json_mode)
        import base64

        content: list[dict] = [{"type": "text", "text": prompt}]
        for data, mime in images:
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(data).decode()}"}})
        return self.chat([{"role": "user", "content": content}], json_mode=json_mode, model=self.vision_model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.embedding_model:
            raise NotImplementedError("no embedding model configured")
        data = self._post("/embeddings", {"model": self.embedding_model, "input": texts})
        return [item["embedding"] for item in data["data"]]


class MetaProvider(OpenAICompatProvider):
    """Meta Model API (Muse Spark). Same wire format, Meta defaults."""

    name = "meta"

    def __init__(self, api_key: str, model: str = "muse-spark-1.3", base_url: str = "https://api.meta.ai/v1", **kw):
        if not api_key:
            raise ValueError("META_API_KEY is required for LLM_PROVIDER=meta")
        super().__init__(base_url, api_key, model, **kw)


class OllamaProvider(OpenAICompatProvider):
    """A Meta Llama model running locally through Ollama (https://ollama.com).

    Ollama speaks the same wire format, needs no real API key, and costs nothing,
    so developers can build and test without spending Meta API tokens.
    """

    name = "llama_local"

    def __init__(self, base_url: str = "http://localhost:11434/v1", model: str = "llama3.2", **kw):
        super().__init__(base_url, "ollama", model, timeout=kw.pop("timeout", 180.0), **kw)
