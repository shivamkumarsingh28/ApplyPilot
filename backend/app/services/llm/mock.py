"""Offline provider used for tests, CI and demos without an API key.

It never invents content. Services check `provider.offline` and switch to their
deterministic code paths (regex extraction, extractive answers), so the product
still works end to end; a real model only improves quality.
"""

from app.services.llm.base import LLMProvider


class MockProvider(LLMProvider):
    name = "mock"
    offline = True

    def chat(self, messages, *, json_mode=False, temperature=0.2, max_tokens=1500) -> str:
        return "{}" if json_mode else ""

    def vision(self, prompt, images, *, json_mode=False) -> str:
        return ""

    def embed(self, texts):
        raise NotImplementedError
