"""Splits page text into overlapping chunks for retrieval."""

from __future__ import annotations

import re

_SENT = re.compile(r"(?<=[.!?])\s+|\n+")
# Abbreviations whose full stop must not end a sentence ("Rs. 250", "No. 12", "Dr. Rao").
_ABBREV = re.compile(r"\b(Rs|No|Nos|Dr|Mr|Mrs|Ms|Sr|Jr|vs|etc|approx|Ref|Adv|Ltd|Govt|Dept)\.", re.I)
_DOT = "\u2024"  # a look-alike dot that the splitter ignores


def split_sentences(text: str) -> list[str]:
    protected = _ABBREV.sub(lambda m: m.group(1) + _DOT, text)
    return [s.replace(_DOT, ".").strip() for s in _SENT.split(protected) if s.strip()]


def chunk_page(text: str, page: int, max_chars: int = 650, overlap_chars: int = 120) -> list[dict]:
    """Group sentences into chunks of roughly `max_chars`, carrying a small overlap.

    Overlap matters: a rule and its exception ("age 21, relaxation 3 years for SC")
    often straddle a boundary, and retrieval should still see them together.
    """
    sentences = split_sentences(text)
    chunks: list[dict] = []
    current = ""
    for sent in sentences:
        if current and len(current) + len(sent) + 1 > max_chars:
            chunks.append({"page": page, "text": current})
            current = current[-overlap_chars:] + " " + sent if overlap_chars else sent
        else:
            current = f"{current} {sent}".strip()
    if current:
        chunks.append({"page": page, "text": current})
    return chunks


def chunk_pages(pages: list[str]) -> list[dict]:
    out: list[dict] = []
    for i, text in enumerate(pages, start=1):
        for c in chunk_page(text, i):
            c["idx"] = len(out)
            out.append(c)
    return out
