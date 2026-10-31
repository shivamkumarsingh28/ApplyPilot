import pytest


def _defaults_only(monkeypatch):
    """Build Settings with no .env file and no inherited env, so only code defaults remain."""
    import app.core.config as cfg

    fields = set(cfg.Settings.model_fields)
    for name in fields:
        monkeypatch.delenv(name.upper(), raising=False)
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(cfg.Settings, "model_config",
                        dict(cfg.Settings.model_config, env_file=None))
    return cfg.Settings()


def test_no_real_credential_is_a_default(monkeypatch):
    s = _defaults_only(monkeypatch)
    for field in ("meta_api_key", "sam_api_key", "openai_compat_key", "google_client_secret",
                  "github_client_secret", "linkedin_client_secret", "brave_api_key", "tavily_api_key"):
        assert getattr(s, field) == "", field
    assert s.llm_provider == "mock" and s.segmenter == "opencv" and s.search_provider == ""


def test_production_rejects_placeholder_secrets(monkeypatch):
    import app.core.config as cfg

    s = _defaults_only(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setattr(cfg, "Settings", lambda: s.__class__(**{**s.model_dump(), "app_env": "production"}))
    cfg.get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            cfg.get_settings()
    finally:
        cfg.get_settings.cache_clear()
