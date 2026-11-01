"""Splits page text into retrieval chunks that keep document structure.

Old behaviour cut text every ~650 characters, so a rule and its exception, a
fee table row and its heading, or a heading and the paragraph under it could
land in different chunks and retrieval missed the answer. Now:

- a chunk never crosses a section heading (heading is stored and prepended),
- table-like lines stay together as one block (each row also becomes a chunk),
- every chunk carries its page, heading, and a larger `parent` block so the
  model sees the rule together with its exceptions.
"""

from __future__ import annotations

import re

_SENT = re.compile(r"(?<=[.!?])\s+|\n+")
# Abbreviations whose full stop must not end a sentence ("Rs. 250", "No. 12", "Dr. Rao").
_ABBREV = re.compile(r"\b(Rs|No|Nos|Dr|Mr|Mrs|Ms|Sr|Jr|vs|etc|approx|Ref|Adv|Ltd|Govt|Dept)\.", re.I)
_DOT = "\u2024"  # a look-alike dot that the splitter ignores

_HEADING = re.compile(
    r"^(?:\d+(?:\.\d+)*[.)]?\s+)?(?:age|eligibility|educational|qualification|selection|application|fee|fees|"
    r"documents?|how to apply|important dates?|vacanc|post|salary|pay|exam|physical|medical|instructions?|"
    r"general conditions?|reservation|relaxation|scheme|scholarship|benefits?|admission|registration|"
    r"last date|starting date|start date|apply online|official)\b.*$", re.I)
_TABLE_ROW = re.compile(r"(\||\t|\b(?:rs\.?|inr|₹)\s*[\d,]+|\b\d+\s*(?:kb|px|years?|%)\b)", re.I)


def split_sentences(text: str) -> list[str]:
    protected = _ABBREV.sub(lambda m: m.group(1) + _DOT, text)
    return [s.replace(_DOT, ".").strip() for s in _SENT.split(protected) if s.strip()]


def _is_heading(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 110:
        return False
    if ":" in line and len(line.split(":", 1)[1].split()) >= 3:
        return False  # "Application fee: Rs. 250 payable..." is content, not a heading
    if re.search(r"(rs\.?|inr|₹|\d+\s*(?:kb|px|years?|%|days)|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\b\d{4}\b)", line, re.I):
        return False  # a line carrying money/measures/a date is content, not a heading
    if line.endswith((".", ",")) or len(line.split()) > 8:
        return False  # headings are short and do not end a sentence
    if _HEADING.match(line):
        return True
    # Short all-caps or colon-terminated lines act as headings in most notices.
    return (line.endswith(":") and len(line.split()) <= 8) or (line.isupper() and 3 <= len(line) <= 80)


def _blocks(text: str) -> list[tuple[str, str]]:
    """Split one page into (heading, block) pairs; consecutive table rows stay in one block."""
    blocks: list[tuple[str, str]] = []
    heading, lines, table = "", [], False

    def flush():
        if lines:
            blocks.append((heading, " ".join(lines).strip()))

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if _is_heading(line):  # headings win: "Application Fee" / "Important Dates" contain no figures
            flush()
            lines, table = [], False
            heading = line.rstrip(":")
            continue
        is_table = bool(_TABLE_ROW.search(line)) and len(line.split()) >= 3
        if table and not is_table and lines:
            flush()
            lines = []
        table = is_table
        lines.append(line)
    flush()
    return [(h, b) for h, b in blocks if b]


def chunk_page(text: str, page: int, max_chars: int = 650, overlap_chars: int = 120) -> list[dict]:
    """Group sentences into chunks of roughly `max_chars`, within one heading block."""
    out: list[dict] = []
    for heading, block in _blocks(text):
        prefix = f"{heading}: " if heading else ""
        sentences = split_sentences(block)
        current = ""
        for sent in sentences:
            if current and len(prefix) + len(current) + len(sent) + 1 > max_chars:
                out.append({"page": page, "heading": heading, "text": prefix + current, "parent": prefix + block})
                current = current[-overlap_chars:] + " " + sent if overlap_chars else sent
            else:
                current = f"{current} {sent}".strip()
        if current:
            out.append({"page": page, "heading": heading, "text": prefix + current, "parent": prefix + block})
    return out


def chunk_pages(pages: list[str]) -> list[dict]:
    out: list[dict] = []
    for i, text in enumerate(pages, start=1):
        for c in chunk_page(text, i):
            c["idx"] = len(out)
            out.append(c)
    return out
