# Chat bot (Telegram, WhatsApp)

Many young people use chat apps all day. The bot lets them ask questions, fix photos and get reminders there.

## What it does

- Ask any question: "What is the last date?", "Am I eligible?" (goes to the assistant, so guardrails and tools apply)
- `/deadlines` lists applications due in 14 days
- Send a picture with caption `photo 3` or `signature 3` (3 = the notice number). You get the fixed file back **as a document**, because chat apps recompress normal photos and that would break the KB limits.
- Daily reminders for deadlines within 3 days (`REMINDER_DAYS`)
- `/link CODE`, `/unlink`, `/help`

## Link your account

1. Website, **Profile**, **Create link code** (valid 10 minutes).
2. In Telegram send `/link YOURCODE` to the bot.

The bot gets its own token that works only for your account.

## Set up Telegram

1. In Telegram talk to **@BotFather**, send `/newbot`, copy the token.
2. In `.env`: `TELEGRAM_BOT_TOKEN=...` and `BOT_TRANSPORT=telegram`. `BOT_SHARED_SECRET` must be the same value for the backend and the bot.
3. Run it:
   ```bash
   cd bot && pip install -r requirements.txt && python -m applypilot_bot.main
   ```
   or `docker compose --profile bot up --build`.

It uses long polling, so you do not need a public address for development.

## Set up WhatsApp (experimental)

The adapter is in `bot/applypilot_bot/transports/whatsapp.py`. It follows Meta's WhatsApp Cloud API but is **not tested with a live number**.

1. Create an app on https://developers.facebook.com and add WhatsApp.
2. Set `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN` (any word you choose), `WHATSAPP_APP_SECRET`, and `BOT_TRANSPORT=whatsapp`.
3. Expose port 8100 on a public HTTPS address and set it as the webhook URL: `https://your-domain/webhook`.
4. Every call is checked with Meta's signature, and bad ones are rejected.

Limits: WhatsApp only lets you message people first with approved templates, so the daily reminders are **not** sent on WhatsApp yet.

## Add another messaging app

Write a transport that turns incoming messages into `core.handle_text(chat_id, text)` or `core.handle_image(chat_id, bytes, caption)` and sends the returned `Reply` objects. All the rules live in `core.py`.

## Privacy

Telegram bot messages are not end-to-end encrypted. The bot's help text tells people never to send passwords or ID numbers.

## Tests

`cd bot && python -m pytest -q` (uses a fake backend, no network).
