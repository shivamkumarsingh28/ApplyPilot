"""PDF compress endpoint: shrink only, never ingest as a notice."""

import base64
import io

from PIL import Image, ImageDraw
from pypdf import PdfWriter


def _pdf_with_image() -> bytes:
    img = Image.new("RGB", (1200, 1600))
    draw = ImageDraw.Draw(img)
    for i in range(0, 1600, 7):
        draw.line([(0, i), (1200, i + 40)], fill=(i % 250, (i * 3) % 250, (i * 7) % 250), width=3)
    out = io.BytesIO()
    img.save(out, "PDF", resolution=150.0)
    return out.getvalue()


def _simple_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(612, 792)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def test_compress_pdf_endpoint(client, auth):
    data = _pdf_with_image()
    r = client.post("/api/v1/pdf/compress", files={"file": ("scan.pdf", data, "application/pdf")},
                    data={"max_kb": "200", "save_to_vault": "true"}, headers=auth)
    assert r.status_code == 200, r.text
    body = r.json()
    out = base64.b64decode(body["data_base64"])
    assert len(out) < len(data)
    assert body["report"]["original_kb"] > body["report"]["final_kb"]
    assert body["document_id"] is not None
    # Saved to the vault as a normal document — NOT ingested as a notice.
    assert client.get("/api/v1/notices", headers=auth).json() == []
    docs = client.get("/api/v1/documents", headers=auth).json()
    assert docs and docs[0]["filename"] == "scan_compressed.pdf"


def test_compress_rejects_non_pdf(client, auth):
    r = client.post("/api/v1/pdf/compress", files={"file": ("x.pdf", b"not a pdf", "application/pdf")}, headers=auth)
    assert r.status_code == 415


def test_compress_pdf_service_keeps_valid_pdf():
    from app.services.pdf_shrink import compress_pdf

    out, info = compress_pdf(_simple_pdf(), max_kb=100)
    assert info["pages"] == 1 and out.startswith(b"%PDF")
