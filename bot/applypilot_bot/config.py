"""Bot settings, read from environment variables."""

import os
from dataclasses import dataclass


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
