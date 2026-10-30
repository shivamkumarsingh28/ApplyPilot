"""Entry point. Choose the messaging app with BOT_TRANSPORT=telegram|whatsapp."""

import logging

from applypilot_bot.api_client import Backend
from applypilot_bot.config import BotSettings
from applypilot_bot.core import BotCore
from applypilot_bot.store import Store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> None:
    s = BotSettings()
    core = BotCore(Backend(s.backend_url, s.bot_secret), Store(s.db_path))
    if s.transport == "telegram":
        from applypilot_bot.transports.telegram import TelegramTransport

        TelegramTransport(s.telegram_token, core).run(s.reminder_days)
    elif s.transport == "whatsapp":
        import uvicorn

        from applypilot_bot.transports.whatsapp import WhatsAppTransport

        app = WhatsAppTransport(core, s.wa_access_token, s.wa_phone_number_id, s.wa_verify_token, s.wa_app_secret).build_app()
        uvicorn.run(app, host="0.0.0.0", port=8100)
    else:
        raise SystemExit(f"Unknown BOT_TRANSPORT: {s.transport}")


if __name__ == "__main__":
    main()
