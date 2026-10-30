"""HTTP client for OpenAI-compatible chat APIs.

Meta Model API (https://api.meta.ai/v1) exposes /chat/completions with Bearer
auth, and the open-weights hosts (Baseten, Fireworks, Modal, vLLM) do too, so one
small client covers all three. Meta-specific defaults live in `MetaProvider`.
"""

from __future__ import annotations

import logging
import time

import httpx

from app.services.llm.base import LLMError, LLMProvider

log = logging.getLogger(__name__)


class OpenAICompatProvider(LLMProvider):
    name = "openai_compat"

    def __init__(self, base_url: str, api_key: str, model: str, *, timeout: float = 90.0, extra_body: dict | None = None,
                 embedding_model: str = "", vision_model: str = "", transport: httpx.BaseTransport | None = None):
        if not base_url or not model:
            raise ValueError("base_url and model are required")
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
                resp.raise_for_status()
                return resp.json()
            except (httpx.HTTPError, ValueError) as exc:  # network, status, or bad JSON
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
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"unexpected response shape: {exc}") from exc

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
