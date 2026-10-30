"""Text embeddings with an offline fallback.

`hash` embeddings use signed feature hashing over unigrams and bigrams. They are
not as good as a neural embedding model but need no network, are deterministic,
and work well enough for retrieval inside a single notice (a few dozen chunks).
"""

from __future__ import annotations

import hashlib
import math
import re

from app.core.config import get_settings
from app.services.llm.factory import get_llm

DIM = 384
_TOKEN = re.compile(r"[a-z0-9]+")
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


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed with the provider when configured, otherwise with the offline hash embedder."""
    if get_settings().embedding_provider == "api":
        try:
            return get_llm().embed(texts)
        except Exception:  # fall back rather than fail an upload
            pass
    return [hash_embed(t) for t in texts]


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))
