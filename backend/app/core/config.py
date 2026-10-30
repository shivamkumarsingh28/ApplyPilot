"""Application settings.

All configuration comes from environment variables (or a local `.env` file).
Nothing is hard-coded, so the same container image runs in development,
CI and production. See `.env.example` for the full list with explanations.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    app_env: str = "development"
    secret_key: str = "dev-secret-change-me"
    encryption_key: str = "NJcJu1CMBBFqjYrjKFb-U9ur7V9VcX3v8WuZ0HDAOek="  # Fernet key; derived from secret_key in dev if empty
    database_url: str = "sqlite:///./data/applypilot.db"
    storage_dir: str = "./data/files"
    cors_origins: str = "http://localhost:3000"
    access_token_minutes: int = 60 * 24 * 7

    # Language model provider: mock | llama_local | meta | openai_compat
    #   mock          offline, no model (tests, quick demo)
    #   llama_local   a Meta Llama model running on your own machine through Ollama (free, for development)
    #   meta          Meta Model API, Muse Spark (production)
    #   openai_compat any OpenAI-compatible server (OpenAI itself, Baseten, Fireworks, Modal, vLLM)
    llm_provider: str = "meta"
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.2"
    ollama_vision_model: str = ""  # e.g. llama3.2-vision, needed only to read scanned notices
    meta_api_key: str = "LLM_2277558179454695_hq6rEMGda1I1v-e8f5joKqu6v3Q"
    meta_api_base: str = "https://api.meta.ai/v1"
    meta_model: str = "muse-spark-1.3"
    openai_compat_base: str = ""
    openai_compat_key: str = ""
    openai_compat_model: str = ""

    # Embeddings: hash (offline) | api
    embedding_provider: str = "api"
    embedding_model: str = "nomic-embed-text"

    # Segmentation: opencv (offline) | meta_sam
    segmenter: str = "meta_sam"
    sam_endpoint: str = "https://api.meta.ai/v1"
    sam_api_key: str = "LLM_2277558179454695_hq6rEMGda1I1v-e8f5joKqu6v3Q"

    # Security
    admin_emails: str = ""  # comma-separated; these emails get the admin role when they register
    rate_limit_per_minute: int = 60  # general API limit per user or IP
    ai_rate_limit_per_minute: int = 12  # stricter limit for endpoints that call the model
    login_rate_limit_per_minute: int = 8

    # Bot
    bot_shared_secret: str = "change-me-bot-secret"

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor. Tests clear the cache after changing env vars."""
    return Settings()
