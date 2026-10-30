"""Provider-neutral interface for language models.

The rest of the codebase only talks to `LLMProvider`. Swapping Meta's Muse Spark
for an open-weights model on Baseten/Fireworks/Modal (or the offline mock) is a
configuration change, not a code change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMError(RuntimeError):
    """Raised when a model call fails after retries."""


class LLMProvider(ABC):
    #: short identifier shown in logs and the /health endpoint
    name: str = "base"
    #: True when no real model is behind the provider (mock). Services use
    #: deterministic fallbacks (regex extraction, extractive answers) when offline.
    offline: bool = False

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        *,
        json_mode: bool = False,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> str:
        """Send chat messages and return the assistant text."""

    def vision(self, prompt: str, images: list[tuple[bytes, str]], *, json_mode: bool = False) -> str:
        """Ask a question about one or more images given as (bytes, mime) pairs."""
        import base64

        content: list[dict] = [{"type": "text", "text": prompt}]
        for data, mime in images:
            b64 = base64.b64encode(data).decode()
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
        return self.chat([{"role": "user", "content": content}], json_mode=json_mode)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding per text. Providers without embeddings raise NotImplementedError."""
        raise NotImplementedError
