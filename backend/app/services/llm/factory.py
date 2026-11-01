"""Builds the configured LLM provider once and caches it.

Default is the Meta Model API (`muse-spark-1.3`). `llama_local` is an optional
backup only. Meta has no embeddings endpoint, so embeddings are configured
separately (see services/embeddings.py) and never routed to Meta by default.
"""

import logging
from functools import lru_cache

from app.core.config import get_settings
from app.services.llm.base import LLMProvider
from app.services.llm.mock import MockProvider
from app.services.llm.openai_compat import MetaProvider, OllamaProvider, OpenAICompatProvider

log = logging.getLogger(__name__)


@lru_cache
def get_llm() -> LLMProvider:
    s = get_settings()
    kind = s.llm_provider.lower()
    if kind == "llama_local":
        return OllamaProvider(s.ollama_base_url, s.ollama_model, vision_model=s.ollama_vision_model)
    if kind == "meta":
        if not s.meta_api_key:
            log.warning("LLM_PROVIDER=meta but META_API_KEY is empty; falling back to offline mock. "
                        "Set META_API_KEY in .env to use the Meta Model API.")
            return MockProvider()
        return MetaProvider(s.meta_api_key, s.meta_model, s.meta_api_base)
    if kind == "openai_compat":
        return OpenAICompatProvider(s.openai_compat_base, s.openai_compat_key, s.openai_compat_model)
    if kind == "mock":
        return MockProvider()
    log.warning("Unknown LLM_PROVIDER=%r; falling back to offline mock.", kind)
    return MockProvider()
