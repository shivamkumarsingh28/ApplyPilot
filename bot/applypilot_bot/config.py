"""Bot settings, read from environment variables / the repo-root `.env`.

Secrets must never be hard-coded here. Local runs read the same repo-root `.env`
as the backend (resolved relative to this file, so the launch folder does not
matter); deployed runs inject real environment variables, which always win.
"""

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv() -> None:
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


@dataclass(frozen=True)
class BotSettings:
    transport: str = os.getenv("BOT_TRANSPORT", "telegram")  # telegram | whatsapp
    backend_url: str = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
    bot_secret: str = os.getenv("BOT_SHARED_SECRET", "change-me-bot-secret")
    db_path: str = os.getenv("BOT_DB_PATH", "./data/bot.db")
    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    # WhatsApp Cloud API (experimental)
    wa_access_token: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    wa_phone_number_id: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    wa_verify_token: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    wa_app_secret: str = os.getenv("WHATSAPP_APP_SECRET", "")
    reminder_days: int = int(os.getenv("REMINDER_DAYS", "3"))
