"""Text embeddings with an offline fallback.

Meta Model API has NO embeddings endpoint, so `api` embeddings go to a separate
OpenAI-compatible embedding endpoint (EMBEDDING_BASE / EMBEDDING_MODEL, e.g. a
hosted multilingual embedder or Ollama `nomic-embed-text`) — never to Meta.
`hash` embeddings use signed feature hashing over unigrams and bigrams: not as
good as a neural model, but deterministic, free, and the safe offline fallback.
The model name is stored on every chunk so two models are never mixed.
"""

from __future__ import annotations

import hashlib
import math
import re

from app.core.config import get_settings

DIM = 384
_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_STOP = {"the", "a", "an", "of", "to", "and", "or", "is", "are", "for", "in", "on", "at", "be", "by", "with", "as", "it"}


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in _STOP]


def hash_embed(text: str) -> list[float]:
    tokens = tokenize(text)
    grams = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
    vec = [0.0] * DIM
    for g in grams:
        h = int.from_bytes(hashlib.blake2b(g.encode(), digest_size=8).digest(), "big")
        vec[h % DIM] += 1.0 if (h >> 63) & 1 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embedding_model_name() -> str:
    s = get_settings()
    if s.embedding_provider == "api" and s.embedding_model:
        return s.embedding_model
    return "hash-v1"


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed with the configured embedding endpoint, otherwise the offline hash embedder."""
    s = get_settings()
    if s.embedding_provider == "api" and s.embedding_model:
        try:
            from app.services.llm.openai_compat import OpenAICompatProvider

            base = s.embedding_base or s.openai_compat_base or s.ollama_base_url
            key = s.embedding_api_key or s.openai_compat_key or "ollama"
            return OpenAICompatProvider(base, key, "", embedding_model=s.embedding_model).embed(texts)
        except Exception:  # fall back rather than fail an upload
            pass
    return [hash_embed(t) for t in texts]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))
