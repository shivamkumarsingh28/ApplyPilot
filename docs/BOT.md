# Chat bot (Telegram, WhatsApp)

Many young people use chat apps all day. The bot lets them ask questions, fix photos and get reminders there.

## What it does

- Ask any question: "What is the last date?", "Am I eligible?" (goes to the assistant, so guardrails and tools apply)
- `/deadlines` lists applications due in 14 days
- Daily reminders for deadlines within 3 days (`REMINDER_DAYS`)
- `/link CODE`, `/unlink`, `/help`

## Tell the bot what to do — captions are instructions

The caption (prompt) decides everything. Nothing destructive happens by default.

### Photos — resize-only by default, background NEVER changes unless asked

| Caption | What happens |
|---|---|
| *(no caption)* | Only the file size is optimised. Background untouched. |
| `resize 200x230` | Exact pixels 200×230. Background untouched. |
| `compress 50kb` / `under 100kb` | Fit under that file size. Background untouched. |
| `resize 300x400 compress 100kb` | Both: exact pixels + max KB. |
| `photo 3` | Use notice 3's photo size/KB rules. **Still no background change.** |
| `photo 3 blue background` / `photo 3 light blue` | Full portal edit: now (and only now) the background may change. |
| `signature 3` | Signature cleaning for notice 3. |
| `document` / `certificate` | Scan cleanup + resize; no face/background work. |

Every result is a preview first — reply `yes` to save it to the vault, `no` to discard.
Files are sent back **as documents**, because chat apps recompress normal photos and that would break the KB limits.

> Why this changed: earlier, any photo caption ran the full photo pipeline, which
> recolours the background to the notice/default colour. Users who only wanted a
> smaller file got a repainted photo. Now `photo_resize` (`change_background=false`)
> is the default and background changes are strictly opt-in.

### PDFs and files — a PDF is a notice only when you say so

| Caption | What happens |
|---|---|
| *(no caption)* on a PDF | Read as a **notice** (RAG ingest — unchanged behaviour). |
| `notice` | Same: read as a notice. |
| `save` / `save to vault` | Stored in the vault **untouched**. Never read, never ingested. |
| `compress` / `compress 500kb` | PDF is shrunk (`POST /pdf/compress`: embedded images re-encoded, streams compressed), sent back and saved to the vault. Text/pages unchanged. |
| Any non-PDF file, no caption | Saved to the vault (it was never readable as a notice anyway). |

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

## Set up WhatsApp

Adapter: `bot/applypilot_bot/transports/whatsapp.py` (Meta WhatsApp Cloud API, Graph v20.0).
It only **replies** — users must message the number first (24-hour window).

### 1. Meta app (developers.facebook.com)

1. Create app → add product **WhatsApp** → **API Setup**.
2. Note the **Phone number ID** (not the phone number itself) and the test number Meta gives you.
3. Add your own mobile number as a recipient (test numbers can only message verified recipients).
4. Copy a token (see expiry warning below) and, from **App Settings → Basic**, the **App Secret**.

### 2. `.env` (repo root — backend and bot share it)

```ini
BOT_TRANSPORT=whatsapp
WHATSAPP_ACCESS_TOKEN=...        # ⚠️ the "Temporary access token" expires in ~24h (error 190 / subcode 463).
WHATSAPP_PHONE_NUMBER_ID=...     # Phone number ID from API Setup, digits only
WHATSAPP_VERIFY_TOKEN=...        # any word YOU invent; must match the dashboard exactly
WHATSAPP_APP_SECRET=...          # App Settings → Basic → App Secret
BOT_SHARED_SECRET=...            # not "change-me-bot-secret"; same value everywhere (shared .env = automatic)
```

For a token that does not expire daily: **Business Settings → Users → System Users** → create one,
assign your app + WhatsApp number, grant `whatsapp_business_messaging` (+ `whatsapp_business_management`),
generate its token and use that as `WHATSAPP_ACCESS_TOKEN`.

### 3. Run backend + bot + public tunnel (3 terminals)

```powershell
# backend (bot calls it for /link, chat, deadlines)
cd backend; python -m uvicorn app.main:app --port 8000   # or your usual backend command
# bot webhook server on :8100
cd bot; .\.venv\Scripts\python.exe -m applypilot_bot.main
# public HTTPS URL for Meta (free ngrok URL changes every restart!)
ngrok http 8100
```

Sanity checks before touching the dashboard:

- `http://localhost:8100/health` → `{"status":"ok",...}`
- `https://<your-ngrok>.ngrok-free.app/webhook?hub.mode=subscribe&hub.verify_token=<WHATSAPP_VERIFY_TOKEN>&hub.challenge=hi` → returns `hi`

### 4. Connect the webhook in the Meta dashboard

WhatsApp → **Configuration → Webhook → Edit**: Callback URL = `https://<your-ngrok>.ngrok-free.app/webhook`,
Verify token = exactly `WHATSAPP_VERIFY_TOKEN`. Click **Verify and save**, then **Manage → subscribe `messages`**.

Restart the bot after any `.env` change — a running bot keeps the old (expired) token in memory.
If the bot receives messages but never replies, read its terminal: Meta errors are now logged
(e.g. `WhatsApp send_text failed: 401 ... code 190` = expired token → generate a fresh one, update `.env`, restart bot).

### 5. Chat with it

1. On the website: **Profile → Create link code** (valid 10 minutes).
2. WhatsApp the test/business number: `/link YOURCODE`, then ask e.g. `What is the last date?`, or send `/deadlines`, `/help`.

Limits: WhatsApp only lets you message people first with approved templates, so daily reminders are **not** sent on WhatsApp yet.

## Add another messaging app

Write a transport that turns incoming messages into `core.handle_text(chat_id, text)` or `core.handle_image(chat_id, bytes, caption)` and sends the returned `Reply` objects. All the rules live in `core.py`.

## Privacy

Telegram bot messages are not end-to-end encrypted. The bot's help text tells people never to send passwords or ID numbers.

## Tests

`cd bot && python -m pytest -q` (uses a fake backend, no network).
