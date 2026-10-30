"""Builds the configured LLM provider once and caches it."""

from functools import lru_cache

from app.core.config import get_settings
from app.services.llm.base import LLMProvider
from app.services.llm.mock import MockProvider
from app.services.llm.openai_compat import MetaProvider, OllamaProvider, OpenAICompatProvider


@lru_cache
def get_llm() -> LLMProvider:
    s = get_settings()
    kind = s.llm_provider.lower()
    if kind == "llama_local":
        return OllamaProvider(s.ollama_base_url, s.ollama_model, embedding_model=s.embedding_model, vision_model=s.ollama_vision_model)
    if kind == "meta":
        return MetaProvider(s.meta_api_key, s.meta_model, s.meta_api_base, embedding_model=s.embedding_model)
    if kind == "openai_compat":
        return OpenAICompatProvider(s.openai_compat_base, s.openai_compat_key, s.openai_compat_model,
                                    embedding_model=s.embedding_model)
    return MockProvider()
