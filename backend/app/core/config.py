"""Application settings.

All configuration comes from environment variables (or a local `.env` file).
No credential is hard-coded: every secret field defaults to empty (or a clearly
labelled dev placeholder) and the real value must come from `.env`/the process
environment. The same container image runs in development, CI and production.
See `.env.example` for the full list with explanations.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .env lives at the repo root and the documented run command cds into backend/,
# so resolve it relative to this file — otherwise settings silently fall back
# to defaults (wrong SAM endpoint, mock-looking config).
_REPO_ENV = Path(__file__).resolve().parents[3] / ".env"
_LOCAL_ENV = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_REPO_ENV if _REPO_ENV.exists() else _LOCAL_ENV), extra="ignore")

    # Core
    app_env: str = "development"
    secret_key: str = "dev-secret-change-me"
    encryption_key: str = ""  # Fernet key; derived from secret_key in dev if empty
    database_url: str = ""
    storage_dir: str = "./data/files"
    cors_origins: str = "http://localhost:3000"
    access_token_minutes: int = 60 * 24 * 7

    # Language model provider: meta | llama_local | mock | openai_compat
    #   meta          Meta Model API, Muse Spark (DEFAULT for dev, testing and production)
    #   llama_local   optional backup: a Meta Llama model on your own machine via Ollama
    #   mock          offline, no model (tests, quick demo)
    #   openai_compat any OpenAI-compatible server (OpenAI itself, Baseten, Fireworks, Modal, vLLM)
    # If meta is selected but META_API_KEY is empty, the factory falls back to
    # mock with a warning so a fresh checkout/tests never crash.
    llm_provider: str = "meta"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.2"
    ollama_vision_model: str = ""  # e.g. llama3.2-vision, needed only to read scanned notices
    meta_api_key: str = ""
    meta_api_base: str = "https://api.meta.ai/v1"
    meta_model: str = "muse-spark-1.3"
    openai_compat_base: str = ""
    openai_compat_key: str = ""
    openai_compat_model: str = ""

    # Embeddings: api | hash (offline fallback)
    # Meta Model API has NO embeddings endpoint, so embeddings always come from
    # a separate embedding model served on an OpenAI-compatible endpoint
    # (EMBEDDING_BASE/EMBEDDING_MODEL), e.g. a hosted multilingual embedder or
    # Ollama `nomic-embed-text`. Unset -> deterministic hash embedder (offline).
    embedding_provider: str = "api"
    embedding_base: str = ""  # empty = reuse the configured LLM endpoint
    embedding_api_key: str = ""
    embedding_model: str = ""

    # Segmentation: opencv (offline) | meta_sam
    segmenter: str = "opencv"
    sam_endpoint: str = ""
    sam_api_key: str = ""

    # Security
    admin_emails: str = ""  # comma-separated; these emails get the admin role when they register
    rate_limit_per_minute: int = 60  # general API limit per user or IP
    ai_rate_limit_per_minute: int = 12  # stricter limit for endpoints that call the model
    login_rate_limit_per_minute: int = 8

    # Bot
    bot_shared_secret: str = "change-me-bot-secret"

    # Phase 2: vault quotas (plan 4.4 starting point, change via env)
    vault_max_file_mb: int = 5
    vault_max_total_mb: int = 50

    # Phase 2: OAuth (plan 3.6). Providers with no credentials stay disabled.
    google_client_id: str = ""
    google_client_secret: str = ""
    github_client_id: str = ""
    github_client_secret: str = ""
    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    oauth_redirect_base: str = "http://localhost:8000"

    # Phase 2: web search (plan 3.7). Never Google Custom Search (sunset 2027-01-01).
    search_provider: str = ""  # brave | tavily (empty = search disabled)
    brave_api_key: str = ""
    tavily_api_key: str = ""
    search_allowed_domains: str = "gov.in,nic.in,ssc.gov.in,upsc.gov.in,ibps.in"

    @property
    def oauth_providers(self) -> list[str]:
        out = []
        if self.google_client_id and self.google_client_secret:
            out.append("google")
        if self.github_client_id and self.github_client_secret:
            out.append("github")
        if self.linkedin_client_id and self.linkedin_client_secret:
            out.append("linkedin")
        return out

    @property
    def search_domain_list(self) -> list[str]:
        return [d.strip().lower() for d in self.search_allowed_domains.split(",") if d.strip()]

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor. Tests clear the cache after changing env vars."""
    s = Settings()
    if s.app_env == "production":
        problems = []
        if s.secret_key in ("", "dev-secret-change-me"):
            problems.append("SECRET_KEY")
        if not s.encryption_key:
            problems.append("ENCRYPTION_KEY")
        if s.bot_shared_secret in ("", "change-me-bot-secret"):
            problems.append("BOT_SHARED_SECRET")
        if problems:
            raise RuntimeError("Production requires real values in .env for: " + ", ".join(problems))
    return s
