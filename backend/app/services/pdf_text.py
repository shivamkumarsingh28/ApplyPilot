"""Turns an uploaded notice (PDF, image or text) into a list of page texts.

Digital PDFs are read directly with pypdf (fast, free, exact). Scanned PDFs and
photos of notices need a vision model, so we render pages to images and ask the
configured multimodal model (Muse Spark accepts image input) to transcribe them.
"""

from __future__ import annotations

import io

from pypdf import PdfReader

from app.services.llm.factory import get_llm

MIN_TEXT_CHARS = 80
TRANSCRIBE_PROMPT = (
    "Transcribe all text on this page exactly as written, preserving numbers, dates and "
    "table rows. Output only the text, no commentary."
)


class UnreadableDocument(ValueError):
    """The document had no extractable text and no vision model is available."""


def _vision_pages(images: list[tuple[bytes, str]]) -> list[str]:
    llm = get_llm()
    if llm.offline:
        raise UnreadableDocument(
            "This looks like a scanned document. Configure LLM_PROVIDER=meta (or openai_compat "
            "with a vision model) so pages can be read."
        )
    return [llm.vision(TRANSCRIBE_PROMPT, [img]).strip() for img in images]


def _render_pdf_pages(data: bytes, scale: float = 2.0) -> list[tuple[bytes, str]]:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(data)
    out = []
    for page in pdf:
        pil = page.render(scale=scale).to_pil()
        buf = io.BytesIO()
        pil.save(buf, format="PNG")
        out.append((buf.getvalue(), "image/png"))
    return out


def extract_pages(data: bytes, filename: str = "", mime: str = "") -> list[str]:
    name = filename.lower()
    if mime.startswith("image/") or name.endswith((".png", ".jpg", ".jpeg", ".webp")):
        return _vision_pages([(data, mime or "image/jpeg")])

    if mime == "application/pdf" or name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        pages = [(p.extract_text() or "").strip() for p in reader.pages]
        if sum(len(p) for p in pages) >= MIN_TEXT_CHARS:
            return pages
        return _vision_pages(_render_pdf_pages(data))

    text = data.decode("utf-8", errors="replace")
    pages = [p.strip() for p in text.split("\f")]  # form feed separates pages in plain text
    return [p for p in pages if p] or [text.strip()]
