"""Photo Studio pro modes: resize-only, document scan, format conversion."""

import base64
import io

from PIL import Image

from app.services.photo_studio import process_document, process_resize


def _img(w=800, h=1000, colour=(120, 60, 30)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), colour).save(buf, "JPEG", quality=92)
    return buf.getvalue()


def _spec(**kw):
    base = {"width": 200, "height": 230, "min_kb": None, "max_kb": None, "format": "jpg", "background": "white"}
    base.update(kw)
    return base


def test_resize_only_exact_pixels_and_colour_untouched():
    out, report = process_resize(_img(), _spec(resize_mode="crop"))
    img = Image.open(io.BytesIO(out))
    assert img.size == (200, 230)
    names = [c["name"] for c in report["checks"]]
    assert "Colour untouched" in names
    assert report["ok"]


def test_resize_only_fit_never_crops():
    out, report = process_resize(_img(1000, 500), _spec(width=200, height=200, resize_mode="fit"))
    img = Image.open(io.BytesIO(out))
    assert img.size == (200, 200)
    assert any("white padding" in c["detail"] for c in report["checks"])


def test_resize_only_hits_exact_kb_range():
    out, report = process_resize(_img(), _spec(min_kb=20, max_kb=50))
    kb = len(out) / 1024
    assert 20 <= kb <= 50, kb
    assert any(c["name"] == "File size" and c["ok"] for c in report["checks"])


def test_format_conversion_jpg_to_png():
    out, report = process_resize(_img(), _spec(format="png"))
    assert out.startswith(b"\x89PNG")
    assert Image.open(io.BytesIO(out)).format == "PNG"


def test_document_mode_no_face_no_background_swap():
    out, report = process_document(_img(900, 1200, (240, 240, 230)), _spec(width=600, height=800, max_kb=100))
    img = Image.open(io.BytesIO(out))
    assert img.size == (600, 800)
    names = [c["name"] for c in report["checks"]]
    assert "Face detected" not in names and "Background" not in names
    assert "Scan cleanup" in names


def test_document_mode_can_skip_enhance():
    out, report = process_document(_img(), _spec(width=None, height=None, enhance=False))
    names = [c["name"] for c in report["checks"]]
    assert "Scan cleanup" not in names


def test_studio_api_modes(client, auth):
    data = _img()
    for kind in ("photo_resize", "document"):
        r = client.post("/api/v1/photo/process",
                        files={"file": ("x.jpg", data, "image/jpeg")},
                        data={"kind": kind, "width": "200", "height": "230", "max_kb": "50"}, headers=auth)
        assert r.status_code == 200, (kind, r.text)
        body = r.json()
        raw = base64.b64decode(body["data_base64"])
        assert Image.open(io.BytesIO(raw)).size == (200, 230)
        assert len(raw) / 1024 <= 50
    bad = client.post("/api/v1/photo/process", files={"file": ("x.jpg", data, "image/jpeg")},
                      data={"kind": "video"}, headers=auth)
    assert bad.status_code == 422
    saved = client.post("/api/v1/photo/process", files={"file": ("x.jpg", data, "image/jpeg")},
                        data={"kind": "photo_resize", "width": "200", "height": "230", "save_to_vault": "true",
                              "save_as": "my-resized-photo"}, headers=auth)
    assert saved.status_code == 200 and saved.json()["document_id"]
    docs = client.get("/api/v1/documents", headers=auth).json()
    assert any(d["filename"] == "my-resized-photo.jpg" for d in docs)
