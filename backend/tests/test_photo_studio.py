import io

from PIL import Image

from app.services.photo_studio import Spec, fit_size, process_photo, process_signature
from tests.conftest import make_jpeg, make_signature_jpeg


def test_photo_meets_spec():
    spec = {"width": 200, "height": 230, "min_kb": 20, "max_kb": 50}
    out, report = process_photo(make_jpeg(), spec)
    img = Image.open(io.BytesIO(out))
    assert img.size == (200, 230)
    assert 20 * 1024 <= len(out) <= 50 * 1024
    assert report["ok"] is True


def test_signature_meets_spec():
    spec = {"width": 140, "height": 60, "min_kb": 10, "max_kb": 20}
    out, report = process_signature(make_signature_jpeg(), spec)
    assert Image.open(io.BytesIO(out)).size == (140, 60)
    assert 10 * 1024 <= len(out) <= 20 * 1024 and report["ok"]


def test_blank_signature_warns():
    blank = Image.new("RGB", (600, 300), (240, 240, 240))
    buf = io.BytesIO()
    blank.save(buf, "JPEG")
    _, report = process_signature(buf.getvalue(), {"width": 140, "height": 60, "max_kb": 20})
    assert report["warnings"]


def test_fit_size_padding_keeps_valid_jpeg():
    img = Image.new("RGB", (50, 50), (255, 255, 255))
    data, info = fit_size(img, Spec(min_kb=15, max_kb=30))
    assert info["padded"] and 15 * 1024 <= len(data) <= 30 * 1024
    assert Image.open(io.BytesIO(data)).size == (50, 50)


def test_impossible_max_is_reported_not_hidden():
    noisy = Image.effect_noise((800, 800), 90).convert("RGB")
    data, info = fit_size(noisy, Spec(max_kb=2))
    assert info["within"] is False
