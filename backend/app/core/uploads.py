"""Upload checks. A file's claimed content type is only a hint, so we look at the bytes."""


def sniff_mime(data: bytes) -> str | None:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if b"\x00" not in data[:4096]:
        try:
            data[:4096].decode("utf-8")
            return "text/plain"
        except UnicodeDecodeError:
            return None
    return None


def matches_claim(data: bytes, claimed: str | None) -> bool:
    """True when the real file type agrees with what the client said it was."""
    real = sniff_mime(data)
    return real is not None and real == (claimed or "")
