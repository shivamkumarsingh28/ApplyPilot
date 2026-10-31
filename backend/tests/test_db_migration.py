import sqlite3


def test_init_db_adds_phase2_columns_to_old_documents_table(tmp_path, monkeypatch):
    db_file = tmp_path / "old.db"
    conn = sqlite3.connect(db_file)
    conn.execute(
        "CREATE TABLE documents (id INTEGER PRIMARY KEY, user_id INTEGER, kind VARCHAR(50), "
        "filename VARCHAR(255), mime VARCHAR(100), size INTEGER, storage_path VARCHAR(500), created_at DATETIME)"
    )
    conn.execute("INSERT INTO documents VALUES (1, 1, 'photo', 'old.jpg', 'image/jpeg', 10, 'x.enc', '2026-01-01')")
    conn.commit()
    conn.close()

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "files"))
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("SEGMENTER", "opencv")
    from app.core import crypto
    from app.core.config import get_settings
    from app.db.session import init_db, reset_engine
    from app.services.llm.factory import get_llm
    from app.services.segmenter import get_segmenter

    for fn in (get_settings, crypto._fernet, get_llm, get_segmenter):
        fn.cache_clear()
    reset_engine()
    from app.core import ratelimit

    ratelimit.reset()
    init_db()
    init_db()  # idempotent: second run must not fail or duplicate columns

    check = sqlite3.connect(db_file)
    cols = [r[1] for r in check.execute("PRAGMA table_info(documents)")]
    assert {"is_original", "original_id", "application_id", "notice_id", "app_ref"} <= set(cols)
    assert check.execute("SELECT filename, is_original, app_ref FROM documents WHERE id=1").fetchone() == ("old.jpg", 1, "")
    reset_engine()


def test_photo_process_on_migrated_shape(client, auth):
    # The normal fixture DB is created by current models; photo vault save is the
    # exact path that failed on the user's pre-Phase-2 database.
    from tests.conftest import make_jpeg

    r = client.post(
        "/api/v1/photo/process",
        files={"file": ("p.jpg", make_jpeg(), "image/jpeg")},
        data={"kind": "photo", "save_to_vault": "true"},
        headers=auth,
    )
    assert r.status_code == 200, r.text
    assert r.json()["document_id"]
