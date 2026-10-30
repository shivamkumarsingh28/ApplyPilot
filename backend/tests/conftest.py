import io
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SAMPLE = Path(__file__).resolve().parents[2] / "samples" / "sample_notice.txt"


@pytest.fixture()
def sample_text() -> str:
    return SAMPLE.read_text().replace("\\f", "\f")


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A TestClient on a throwaway database and storage directory, using the offline mock model."""
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/test.db")
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "files"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("SEGMENTER", "opencv")
    from app.core import crypto
    from app.core.config import get_settings
    from app.db.session import reset_engine
    from app.services.llm.factory import get_llm
    from app.services.segmenter import get_segmenter

    for fn in (get_settings, crypto._fernet, get_llm, get_segmenter):
        fn.cache_clear()
    reset_engine()
    from app.core import ratelimit

    ratelimit.reset()
    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c


@pytest.fixture()
def auth(client):
    r = client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "password123", "full_name": "Asha Verma"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def make_jpeg(size=(1200, 1600), color=(90, 120, 160)) -> bytes:
    img = Image.new("RGB", size, color)
    d = ImageDraw.Draw(img)
    d.ellipse((400, 300, 800, 800), fill=(224, 172, 140))
    d.rectangle((300, 800, 900, 1600), fill=(40, 40, 90))
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


def make_signature_jpeg() -> bytes:
    img = Image.new("RGB", (1000, 500), (230, 230, 225))
    ImageDraw.Draw(img).line([(100, 300), (300, 150), (500, 320), (800, 200)], fill=(20, 20, 60), width=9)
    buf = io.BytesIO()
    img.save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture()
def db_ctx(client):
    """A ToolContext for a freshly registered user, for tests that call tools directly."""
    from app.db import session as session_module
    from app.db.models import User
    from app.services.agents.tools import ToolContext

    client.post("/api/v1/auth/register", json={"email": "ctx@example.com", "password": "password123"})
    db = next(session_module.get_db())
    yield ToolContext(db=db, user=db.query(User).first())
    db.close()
