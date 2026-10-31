# ApplyPilot Bot — Complete Code Document

This is the **only document file created for this folder**, as requested. It is not called README.
Its purpose is simple: read this from top to bottom and you will understand **what every folder,
every file, and every important line of code does**, so you can confidently add more features later.

> ⚠️ **Security warning found while writing this document:** `applypilot_bot/config.py` (line 12)
> currently has a **real-looking Telegram bot token hard-coded as the default value** in the code.
> A bot token is a password for your bot. If this code was ever shared or pushed anywhere, that token
> must be considered leaked: open Telegram → **@BotFather** → `/mybots` → your bot → **API Token → Revoke current token**,
> then put the new token ONLY in `.env` as `TELEGRAM_BOT_TOKEN` (never in code). This document does not copy the token.

---

## Table of contents

1. [The one idea behind the whole folder](#1-the-one-idea-behind-the-whole-folder)
2. [Folder map](#2-folder-map)
3. [End-to-end flows (how a message travels)](#3-end-to-end-flows-how-a-message-travels)
4. [File-by-file, line-by-line](#4-file-by-file-line-by-line)
   - 4.1 `applypilot_bot/main.py` — entry point
   - 4.2 `applypilot_bot/config.py` — settings
   - 4.3 `applypilot_bot/core.py` — the brain (biggest file, read carefully)
   - 4.4 `applypilot_bot/api_client.py` — talks to the backend
   - 4.5 `applypilot_bot/store.py` — the bot's tiny database
   - 4.6 `applypilot_bot/reminders.py` — deadline reminders
   - 4.7 `applypilot_bot/transports/telegram.py` — Telegram adapter
   - 4.8 `applypilot_bot/transports/whatsapp.py` — WhatsApp adapter
   - 4.9 `tests/test_core.py` — how the tests prove it works
   - 4.10 Small files: `requirements.txt`, `Dockerfile`, `__init__.py`, `.venv`, `.pytest_cache`, `data/`
5. [The bot's database tables](#5-the-bots-database-tables)
6. [Every command and conversation the user can have](#6-every-command-and-conversation-the-user-can-have)
7. [Configuration reference (`.env` variables)](#7-configuration-reference-env-variables)
8. [How to run it](#8-how-to-run-it)
9. [How to test it](#9-how-to-test-it)
10. [How to add a new feature (recipes)](#10-how-to-add-a-new-feature-recipes)
11. [Known limitations and things to improve](#11-known-limitations-and-things-to-improve)
12. [Glossary](#12-glossary)

---

## 1. The one idea behind the whole folder

The bot is split into **two layers**, and almost every design decision follows from this:

```
Telegram / WhatsApp  ──►  TRANSPORT (thin adapter)  ──►  CORE (all the rules)  ──►  BACKEND API
   (the chat app)          telegram.py / whatsapp.py        core.py               (backend/ folder)
```

- **Transports are thin.** A transport only knows how to *receive* a message from one chat app and
  *send* a reply back to that same app. It contains **no business rules**.
- **The core is shared.** All intelligence — "is this user linked?", "which notice are we talking
  about?", "the user said *yes*, send the final photo" — lives in `core.py` (`BotCore`).
  Telegram and WhatsApp both call the exact same core functions.
- **The bot stores almost nothing.** The bot never reads notices, checks eligibility, or resizes
  photos itself. It asks the **backend** (the `backend/` folder, an HTTP API) to do all of that.
  The bot only remembers: *which chat belongs to which account*, *what conversation step the user
  is in*, and *which reminders were already sent today*.

**Why this matters for you:** to support a new chat app (say, Signal), you write **one new transport
file** and touch nothing else. To change a rule (say, the photo flow), you edit **one place in
core.py** and both Telegram and WhatsApp get the change.

The contract between the layers is the `Reply` object (core.py line 46-48):

```python
@dataclass
class Reply:
    text: str | None = None                                  # a text message to send, or None
    file: tuple[bytes, str, str] | None = None               # (file bytes, filename, mime) or None
```

Core functions always return a **list of `Reply`** (`list[Reply]`) — usually one reply, sometimes
two (e.g. a photo preview = one text reply + one file reply). Transports loop over the list and
deliver each item. The core never talks to Telegram/WhatsApp directly. This is what makes the
core testable without any real chat app.

---

## 2. Folder map

```
bot/
├── DOCUMENT.md                  ◄── this file (the only document created)
├── Dockerfile                   how to build a container image of the bot
├── requirements.txt             the 4 Python packages the bot needs
├── applypilot_bot/              the actual Python package (the code that runs)
│   ├── __init__.py              empty file; its existence makes this folder a Python package
│   ├── main.py                  START HERE: entry point, chooses telegram or whatsapp
│   ├── config.py                all settings, read from environment variables (.env)
│   ├── core.py                  THE BRAIN: every rule, command and conversation (246 lines)
│   ├── api_client.py            every HTTP call to the backend, in one place (class Backend)
│   ├── store.py                 tiny SQLite database: links, conversation state, reminders
│   ├── reminders.py             "deadline in 2 days!" — once per application per day
│   └── transports/
│       ├── __init__.py          empty; makes transports/ a sub-package
│       ├── telegram.py          Telegram adapter (long polling, no public URL needed)
│       └── whatsapp.py          WhatsApp Cloud API adapter (webhook + signature check)
├── tests/
│   ├── __init__.py              empty; makes tests/ a package
│   └── test_core.py             13 tests using a fake in-memory backend (no network, no real bot)
├── data/
│   └── bot.db                   the bot's SQLite database file (created automatically, git-ignored)
├── .venv/                       this machine's Python virtual environment (git-ignored, do not edit)
└── .pytest_cache/               pytest's cache folder (git-ignored, safe to delete)
```

**What is NOT in this folder:** the backend API (`backend/`), the website (`frontend/`), the browser
extension (`extension/`). The bot is a *client* of the backend — it calls it over HTTP.

---

## 3. End-to-end flows (how a message travels)

### Flow A — user asks a question on Telegram

```
1. User types "What is the last date?" in Telegram.
2. Telegram servers hold the message. The bot is *polling* (asking every ~30s, see telegram.py run()).
3. telegram.py parse_update() turns Telegram's JSON into an Incoming(chat_id, text=...).
4. TelegramTransport.handle() sees it's text → calls core.handle_text(chat_id, text).
5. BotCore checks: is this chat linked? (store.token(chat_id)) — if not, reply "link your account".
6. BotCore finds the current notice (the one from /use, or the only one the user has).
7. BotCore calls backend.chat(token, question, notice_id) → POST /api/v1/assistant/chat.
   The BACKEND does the AI work (retrieval, answer). The bot does none of it.
8. Backend returns {"answer": "..."}. BotCore splits long answers into ≤1000-char pieces (split_text).
9. BotCore returns [Reply(text=...), ...]. telegram.py deliver() sends each with sendMessage.
```

### Flow B — user sends a notice PDF (background ingest)

```
1. User sends the PDF as a Telegram *document*.
2. parse_update() marks it is_document=True (mime does not start with image/).
3. core.handle_document() checks: linked? file ≤ 5 MB? → backend.upload_notice()
   → POST /api/v1/jobs/ingest. The backend starts a BACKGROUND job and returns a job id instantly.
4. Bot replies immediately: "Got it, reading your notice. I will message you when it is ready."
   (This instant reply is the whole point: Telegram/WhatsApp drop slow responses.)
5. telegram.py polls core.poll_job() every 2s, up to 30 times (~60s): GET /api/v1/jobs/{id}.
6. When status is ready, poll_job() builds the summary ("Last date: ...", "Age: ...") from the
   backend's pre-computed key answers, remembers this as the user's current notice, and the
   transport delivers it. The user can now ask questions (Flow A).
```

### Flow C — user sends a photo (preview → confirm)

```
1. User sends a photo with caption "photo 3 light blue" (3 = notice number, colour optional).
2. telegram.py downloads the largest photo size; core.handle_image() runs.
3. Core parses the caption: "sign..." → signature, otherwise photo; first number → notice id;
   colour words/#hex → background colour.
4. backend.photo() → POST /api/v1/photo/process. Backend resizes, fixes background, checks the
   rules, saves a copy to the user's vault, returns the file bytes + a pass/fail report.
5. Core STASHES the result in store state "pending_photo" and returns preview text + the file.
6. User replies "yes" → handle_text sees pending_photo → _confirm_photo() re-sends the final file
   as a document (exact bytes — chat apps recompress normal photos and would break KB limits).
   User replies "no" → the stash is cleared and the file is discarded.
```

### Flow D — eligibility with missing date of birth

```
1. User sends /eligible. Core calls backend.eligibility(token, notice_id).
2. Backend says missing_profile_fields includes "dob" → core sets state awaiting_dob=1 and asks:
   "Please send your date of birth (DD/MM/YYYY)..."
3. User's next message is checked FIRST against the pending state (before any command parsing):
   if it matches DD/MM/YYYY, _save_dob() validates it is a real calendar date, loads the profile
   from the backend, sets dob, saves it back (PUT /profile), clears the state, and tells the
   user to send /eligible again.
```

### Flow E — reminders (Telegram only, automatic)

```
Every hour, telegram.py run() calls reminders.run_once(): for every linked chat, ask the backend
for applications due within N days (default 3), skip ones already reminded today (store table
"reminders"), send "Reminder: X closes on ... (2 days left)", and mark them sent.
WhatsApp does not run reminders: Meta only allows business-initiated messages via approved
templates outside the 24-hour reply window (see the note at the top of whatsapp.py).
```

---

## 4. File-by-file, line-by-line

Line numbers refer to the files as they are today. When a line is trivial (blank line, closing
bracket), it is grouped with its neighbours instead of explained alone.

### 4.1 `applypilot_bot/main.py` — entry point (32 lines)

*Purpose: start the bot. Nothing else.*

| Lines | What it does and why |
|---|---|
| 1 | Docstring: the one-line job description + how to choose the app (`BOT_TRANSPORT`). |
| 3 | `import logging` — Python's standard logging. |
| 5-8 | Imports the four building blocks: `Backend` (API client), `BotSettings` (config), `BotCore` (brain), `Store` (database). |
| 10 | `logging.basicConfig(...)` — turns logging on, INFO level, format `time LEVEL name: message`. Without this, `log.info(...)` calls elsewhere would print nothing. |
| 13 | `def main() -> None:` — the single entry function. |
| 14 | `s = BotSettings()` — reads all environment variables into one frozen object. |
| 15 | Builds the core: `BotCore(Backend(s.backend_url, s.bot_secret), Store(s.db_path))`. This is the **wiring**: the brain gets an API client (how to reach the backend + the shared secret) and a database (where links/state live). Everything else uses these two. |
| 16 | `if s.transport == "telegram":` — first branch of the transport choice. |
| 17 | Telegram import is **inside** the branch (lazy import): the WhatsApp-only dependencies are never imported in Telegram mode and vice versa. |
| 19 | `TelegramTransport(s.telegram_token, core).run(s.reminder_days)` — create the Telegram adapter and start its infinite polling loop. This line never returns while the bot is alive. |
| 20 | `elif s.transport == "whatsapp":` — second branch. |
| 21 | `import uvicorn` — the web server, only needed for WhatsApp webhooks. |
| 23 | WhatsApp import (lazy, same reason as line 17). |
| 25 | Build the FastAPI webhook app from the WhatsApp adapter. |
| 26 | `uvicorn.run(app, host="0.0.0.0", port=8100)` — serve it on port 8100. `0.0.0.0` means "accept connections from outside this machine" — required because Meta's servers must reach your webhook over the public internet (via a tunnel like ngrok in development). |
| 27-28 | `else: raise SystemExit(...)` — any other `BOT_TRANSPORT` value is a configuration error; fail loudly at startup instead of silently doing nothing. |
| 31-32 | `if __name__ == "__main__": main()` — standard Python idiom: run `main()` only when this file is executed directly (`python -m applypilot_bot.main`), not when imported. |

### 4.2 `applypilot_bot/config.py` — settings (19 lines)

*Purpose: every setting in one place, all from environment variables (your `.env` file).
No setting is read anywhere else in the code — if you add one, add it here.*

| Lines | What it does and why |
|---|---|
| 1 | Docstring. |
| 3-4 | Imports: `os` (to read environment variables), `dataclass` (a shortcut for settings classes). |
| 7 | `@dataclass(frozen=True)` — `frozen=True` means settings cannot be changed after creation; a bug that tries `s.transport = ...` crashes instead of silently corrupting behaviour. |
| 8 | `class BotSettings:` — one object holding everything. |
| 9 | `transport` — `BOT_TRANSPORT`, default `"telegram"`. Which chat app to serve. |
| 10 | `backend_url` — where the backend API lives, default `http://localhost:8000`; `.rstrip("/")` removes a trailing slash so URL building in api_client.py never produces `//`. |
| 11 | `bot_secret` — `BOT_SHARED_SECRET`, the shared password between bot and backend. The backend only accepts the `/bot/link` call if this header matches. **Must be identical in the bot's and backend's `.env`.** |
| 12 | `db_path` — where the bot's SQLite file lives, default `./data/bot.db`. ⚠️ **This line currently also contains a hard-coded Telegram token as the `telegram_token` default on the next line — see the security warning at the top of this document.** |
| 13 | `telegram_token` — `TELEGRAM_BOT_TOKEN` from @BotFather. (The hard-coded fallback here must be removed — tokens belong only in `.env`.) |
| 14 | Comment: WhatsApp settings are experimental (adapter written from Meta's docs, not yet tested on a live number at the time of writing). |
| 15 | `wa_access_token` — `WHATSAPP_ACCESS_TOKEN`: Meta's token used in the `Authorization: Bearer` header for every WhatsApp API call. |
| 16 | `wa_phone_number_id` — `WHATSAPP_PHONE_NUMBER_ID`: the ID (not the number itself) of your WhatsApp Business phone number; it appears in every API URL. |
| 17 | `wa_verify_token` — `WHATSAPP_VERIFY_TOKEN`: any string **you invent**; Meta sends it back during webhook setup and the bot checks it matches (proves the webhook is yours). |
| 18 | `wa_app_secret` — `WHATSAPP_APP_SECRET`: used to verify that incoming webhooks really came from Meta (HMAC signature, whatsapp.py). |
| 19 | `reminder_days` — how many days ahead reminders look, default 3. `int(...)` because environment variables are always strings. |

### 4.3 `applypilot_bot/core.py` — the brain (246 lines)

*Purpose: every rule and conversation. Transports call three entry points —
`handle_text`, `handle_image`, `handle_document` — plus `poll_job`. Everything prefixed `_` is a private helper.*

#### Top of file: constants and helpers (lines 1-56)

| Lines | What it does and why |
|---|---|
| 1-6 | Docstring stating the architecture contract: transports convert messages → core calls → `Reply` objects. "All rules live here, so a new transport only needs to read and write messages." |
| 8 | `from __future__ import annotations` — lets type hints like `str \| None` work on older Pythons and keeps hints cheap (not evaluated at import). |
| 10-11 | Imports: `re` (regex, used for captions/dates/colours) and `dataclass`. |
| 13-14 | Imports `Backend, BackendError` (API client + its exception) and `Store`. The core depends on these two and nothing else — that's why tests can substitute fakes. |
| 16-25 | `HELP` — the exact help text sent for `/help`, `/start`. It documents the three things a user can do (send a notice PDF, ask questions, send photo/signature) and lists all commands. Keeping it a module constant means both transports show identical text. |
| 27 | `MAX_DOC_BYTES = 5 * 1024 * 1024` — 5 MB upload limit for notice documents, enforced before anything is sent to the backend (saves bandwidth and matches the backend's limit). |
| 28 | `_DOB_RE` — regex for a date of birth typed as DD/MM/YYYY (also accepts `-` or `.` as separators). `^...$` anchors mean the *whole* message must be the date — "my dob is 05/08/2004" does not match, which is deliberate (avoids false saves). |
| 29 | `_COLOUR_RE` — matches a background colour inside a photo caption: either a `#hex` value like `#e6f0ff` or one of the known colour names (`light blue`, `white`, …). Case-insensitive (`re.I`). |
| 32-44 | `split_text(text, limit=1000)` — splits a long answer into ≤1000-char messages because chat apps truncate long messages. It splits on sentence ends (`. `, `! `, `? `) or newlines, greedily packs sentences into chunks, and never produces an empty chunk. Note it can slightly exceed 1000 if a single "sentence" is longer than the limit (the final `or [text[:limit]]` only guards the empty case) — harmless, since transports also cap at 4000. |
| 45 | `LINK_HELP` — the exact sentence telling an unlinked user how to link (website → Profile → Create link code → `/link CODE`). Reused in several replies. |
| 48-51 | `Reply` dataclass — the **only** thing core functions return (inside a list). `text` = a message to send; `file` = `(bytes, filename, mime)` to send as a document. A reply can have text, a file, or both fields set (transports check each). |
| 54-56 | `class BotCore` + `__init__` — the constructor just stores the two collaborators: `self.backend` (API client) and `self.store` (database). No other state is kept in memory — all conversation state lives in the store, so restarting the bot loses nothing. |

#### `handle_text` — every text message (lines 59-107)

This is the **router** of the bot. The order of checks is important and deliberate:

| Lines | What it does and why |
|---|---|
| 60 | Signature: takes `chat_id` (who) and `text` (what they typed), returns `list[Reply]`. |
| 61 | `text = (text or "").strip()` — tolerate `None`, remove surrounding whitespace so `" /help "` still works. |
| 62 | `cmd, _, arg = text.partition(" ")` — split into first word (`cmd`) and the rest (`arg`). `"/link ABC123"` → cmd=`/link`, arg=`ABC123`. |
| 63 | `cmd = cmd.lower().split("@")[0]` — lowercases, and strips a `@BotName` suffix (Telegram appends it to commands in group chats, e.g. `/help@ApplyPilotBot`). |
| 64-65 | `/start` or `/help`: if already linked show `HELP`; if not, show a welcome + `LINK_HELP`. First impressions matter — an unlinked user must not see commands they can't use yet. |
| 66-67 | `/link` → delegate to `_link()` with the code. Works **before** linking (obviously) — that's why it's above the link check. |
| 68-70 | `/unlink`: delete the chat→account link from the store and confirm. Also above the link check, so it works even if the token had expired. |
| 71-73 | `token = self.store.token(chat_id)` — from here on, everything needs a linked account. If there is no token, reply `LINK_HELP` and stop. **No backend call is ever made for an unlinked chat** (a test proves this). |
| 74 | `try:` — everything below calls the backend; failures are converted to friendly messages by the `except` at line 106. |
| 76-80 | **Pending state first: DOB.** If state `awaiting_dob` is set, this message *is* the DOB answer: if it matches `_DOB_RE`, save it (`_save_dob`); otherwise re-ask. This check must come before command parsing, or a date could be mistaken for a question. |
| 81-86 | **Pending state second: photo confirmation.** If `pending_photo` is set and the user typed `yes`/`y` → `_confirm_photo()`; `no`/`n` → clear the stash and confirm discard. Any *other* text falls through and is treated as a normal message (the stash stays — maybe not ideal, see §11). |
| 87-88 | `/deadlines` → `backend.deadlines(token)` and format with `_format_deadlines`. |
| 89-94 | `/notices` → list the user's notices as `#id Title` (max 10, title cut at 60 chars) and tell them about `/use`. Empty list gets a friendly "send me a PDF" message. |
| 95-99 | `/use N` → validate `N` is all digits, save it as state `notice_id` ("the notice we're talking about"), confirm. This saved value is what makes follow-up questions work without repeating the number. |
| 100-101 | `/eligible` or `/eligibility` → `_eligibility()`. |
| 102 | Anything else is a **question**: find the current notice (`_current_notice`)… |
| 103 | …and ask the backend: `backend.chat(token, text, notice_id)["answer"]`. All the AI/RAG work happens in the backend; the bot just forwards the question and the notice context. |
| 104 | Split the answer with `split_text` and return one `Reply` per piece. |
| 105-106 | `except BackendError as exc: return [self._error(chat_id, exc)]` — every backend failure (expired token, rate limit, server down) becomes one friendly reply instead of a crash. |

#### The helpers (lines 108-244)

| Lines | What it does and why |
|---|---|
| 108-115 | `_current_notice(chat_id, token)` — "which notice are we talking about?" Priority: (1) the notice saved by `/use` or by a finished ingest; (2) if the user has **exactly one** notice, that one (no need to ask); (3) otherwise `None` (callers must ask the user). |
| 117-128 | `_eligibility(chat_id, token)` — Flow D above. Gets the current notice (asks if ambiguous), calls `backend.eligibility`, and if the backend reports `dob` missing, sets `awaiting_dob` and asks for it (it never guesses an age). Otherwise formats the verdict + one line per check + the "confirm with the official notice" disclaimer, split for chat. |
| 130-141 | `_save_dob(chat_id, token, m)` — builds a real `date` from the regex groups (day, month, year order!). `ValueError` (e.g. 31/02/2004) → "that date does not exist" and the state stays set so they can retry. On success: load the full profile from the backend, set `dob` in ISO format (`2004-08-05`), save the whole profile back, clear the state, and confirm with the date formatted back as DD/MM/YYYY. Note: it sends the **whole profile** back because the backend's profile save replaces it — loading first prevents wiping other fields. |
| 144-155 | `handle_document(chat_id, data, filename, mime, caption)` — Flow B. Guards: must be linked; ≤5 MB. Then `backend.upload_notice()` creates the background job, the job id is stored as state `job_id`, and the instant acknowledgement is returned. The caption parameter is accepted but currently unused (a future hook — e.g. "this is for notice 3"). |
| 157-177 | `poll_job(chat_id)` — asks the backend for the stored job's status. Still working (`queued`/`reading`/`indexing`) → a "Still …" progress reply (note: Telegram's polling loop ignores these and only delivers the final one — see §11). Finished → clear `job_id`; `failed` → relay the backend's error; `ready` → adopt the notice as current (`notice_id` state) and build the summary from the backend's pre-computed key-answer lines. Returns `[]` when there is nothing to say (no job, or backend hiccup) so transports can call it safely any time. |
| 179-186 | `_link(chat_id, code)` — no code → usage example. Otherwise `backend.link(code.upper(), chat_id)` (codes are case-insensitive, hence `.upper()`); on success the backend returns a long-lived access token, which is stored against this chat. From now on, `store.token(chat_id)` identifies the user to the backend. |
| 188-192 | `_format_deadlines(rows)` — static helper (no `self` needed): empty → "No open applications…", else one `- Title: date (N days left)` line per row, titles cut at 60 chars. |
| 194-200 | `_error(chat_id, exc)` — translates backend errors: **401** → the token died, so unlink the chat and tell the user to link again (self-healing); **429** → "asking too fast, wait a minute"; anything else → "something went wrong: <detail>". The detail is included for other errors because it usually explains the real problem (e.g. file too large). |
| 203-232 | `handle_image(chat_id, image, caption)` — Flow C. Parses the caption: contains "sign" (case-insensitive) → signature, else photo; first number → notice id; colour match → background. If no notice id: use the current notice; if still ambiguous and the user has >1 notice, reply with the numbered list and ask them to resend with a caption. Then `backend.photo(...)` does all image work server-side. The result is stashed as JSON in state `pending_photo` (bytes base64-encoded so it fits in a text column) and returned as preview text + file. |
| 234-244 | `_confirm_photo(chat_id, token)` — reads and **clears** the stash first (so "yes" can't be replayed twice), decodes the file, and returns the confirmation text + final file. Corrupt/missing stash → "preview expired, send it again" instead of a crash. The `token` parameter is currently unused (the file was already saved to the vault by the backend during `handle_image`) — kept for symmetry/future use. |

### 4.4 `applypilot_bot/api_client.py` — talks to the backend (70 lines)

*Purpose: every HTTP call the bot makes, in one class. If the backend adds an endpoint the bot
needs, this file gets one new method and core.py calls it.*

| Lines | What it does and why |
|---|---|
| 1 | Docstring: "on behalf of one linked chat" — every call carries one user's token. |
| 3 | `import base64` — photo results come back base64-encoded inside JSON; decoded here. |
| 5 | `import httpx` — the HTTP library (also used for the mock transport in tests). |
| 8-11 | `BackendError(Exception)` — the one exception type the core must handle. Carries the HTTP `status` and a human-readable `detail`, because `_error()` in core.py behaves differently for 401/429/other. |
| 14-18 | `Backend.__init__(base_url, bot_secret, transport=None)` — stores the base URL (normalised to end with `/api/v1`), the shared bot secret, and an `httpx.Client` with a generous 120s timeout (photo processing and ingest uploads can be slow). The optional `transport` parameter exists **for tests**: they inject `httpx.MockTransport` so no real network is used. |
| 20-31 | `_send(method, path, token=None, **kw)` — the single funnel for all calls. Adds `Authorization: Bearer <token>` when a user token is given, performs the request, and on any status ≥400 extracts `detail` from the JSON error body (falling back to raw text) and raises `BackendError`. On success returns the parsed JSON. Funnelling means auth headers and error handling can never be forgotten by a new endpoint method. |
| 33-35 | `link(code, chat_id)` — `POST /bot/link` with the code and chat id, plus the `X-Bot-Secret` header (this call has no user token yet — the secret is what authorises it). Returns the `access_token` the backend issues for this chat. |
| 37-38 | `chat(token, message, notice_id=None)` — `POST /assistant/chat`: the question-answering call (Flow A). `notice_id` may be `None`, in which case the backend's assistant decides/asks. |
| 40-41 | `deadlines(token, days=14)` — `GET /applications/upcoming?days=N`: applications due soon; used by `/deadlines` and by reminders. |
| 43-44 | `notices(token)` — `GET /notices`: the user's notice list (`id`, `title`, …). Used by `/notices`, `_current_notice`, and the photo ambiguity check. |
| 46-54 | `photo(token, image, kind, notice_id, background=None)` — `POST /photo/process` as multipart form: the image file, `kind` (photo/signature), `save_to_vault=true` (bot photos are always vaulted), plus notice id and background colour when known. The response JSON contains the processed file as base64; line 53 decodes it into real `bytes` and attaches it as `res["bytes"]` so core.py never deals with base64 at the API boundary. |
| 56-58 | `upload_notice(token, data, filename, mime)` — `POST /jobs/ingest` (multipart) with `source="bot"` so the backend can tell chat uploads from website uploads. Returns `{job_id, status}`. |
| 60-61 | `job(token, job_id)` — `GET /jobs/{id}`: poll a background ingest job (status, summary lines, notice id). |
| 63-64 | `profile(token)` — `GET /profile`: the user's full profile dict. |
| 66-67 | `save_profile(token, data)` — `PUT /profile`: replaces the profile. Used only by the DOB flow (which loads first, edits one field, saves — see `_save_dob`). |
| 69-70 | `eligibility(token, notice_id)` — `GET /notices/{id}/eligibility`: the deterministic eligibility verdict + per-rule checks + `missing_profile_fields`. |

### 4.5 `applypilot_bot/store.py` — the bot's tiny database (50 lines)

*Purpose: the only place the bot persists anything. Three small tables in one SQLite file.*

| Lines | What it does and why |
|---|---|
| 1 | Docstring summarising the two original jobs (links, reminders); a third table (`state`) was added for conversations. |
| 3-5 | Imports: `os` (create folders), `sqlite3` (built-in database — no server needed), `date` (for "today" in reminders). |
| 8 | `class Store` — one instance for the whole bot process (created in main.py). |
| 9-16 | `__init__(path)` — creates the parent folder if needed (skipped for the special `":memory:"` path used by tests, which gives a throwaway DB), opens the connection with `check_same_thread=False` (the Telegram poll loop and reminder calls share it), then creates the three tables **if they don't exist**: `links(chat_id PK, token)`, `reminders(chat_id, app_id, sent_on, PK all three)` — the composite primary key is what makes "once per application per day" enforceable — and `state(chat_id, key, value, PK chat_id+key)` — generic key/value per chat. Finally `commit()`. |
| 18-20 | `set_state(chat_id, key, value)` — `INSERT OR REPLACE`: writes or overwrites one state value (e.g. `notice_id=3`, `awaiting_dob=1`, `pending_photo=<json>`). |
| 22-24 | `get_state(chat_id, key)` — returns the value or `None`. Core treats `None` as "not in that conversation step". |
| 26-28 | `clear_state(chat_id, key)` — deletes one state row; used when a step finishes (DOB saved, photo confirmed/discarded, job done). |
| 30-32 | `link(chat_id, token)` — `INSERT OR REPLACE` so re-linking a chat simply replaces the old token. |
| 34-36 | `unlink(chat_id)` — deletes the link row (`/unlink`, or automatic on a 401). Note: state rows for the chat are not deleted — harmless, and re-linking keeps the chosen notice. |
| 38-40 | `token(chat_id)` — the link lookup used by **every** core entry point before touching the backend. |
| 42-43 | `all_chats()` — every `(chat_id, token)` pair; reminders iterate this. |
| 45-46 | `reminded_today(chat_id, app_id)` — existence check for today's reminder row. |
| 48-50 | `mark_reminded(chat_id, app_id)` — `INSERT OR IGNORE` today's row (ignore = safe if called twice). |

### 4.6 `applypilot_bot/reminders.py` — deadline reminders (31 lines)

| Lines | What it does and why |
|---|---|
| 1 | Docstring: one reminder per application per day. |
| 5 | `Callable` type import — `run_once` receives the transport's send function as a value, so this file doesn't import Telegram/WhatsApp (keeps the layering clean). |
| 7-8 | Imports `Backend/BackendError` and `Store` (types only — instances are passed in). |
| 11-24 | `due_reminders(backend, store, days)` — the pure decision part (returns messages instead of sending them, which is what makes it unit-testable): for each linked chat, fetch upcoming deadlines (a `BackendError` for one chat — e.g. an expired token — is caught and that chat is skipped, never crashing the whole round); skip applications already reminded today; build the message text; **mark as reminded immediately** (before returning), so a crash later can't cause duplicate sends on the next round. Returns `[(chat_id, message), ...]`. |
| 27-31 | `run_once(backend, store, days, send_text)` — the side-effecting wrapper: get due pairs, call `send_text(chat_id, message)` for each, return how many were sent. Telegram's run loop calls this hourly; a future WhatsApp/admin trigger could call it too. |

### 4.7 `applypilot_bot/transports/telegram.py` — Telegram adapter (111 lines)

*Purpose: translate between Telegram's Bot API and `BotCore`. Long polling: the bot asks Telegram
"anything new?" in a loop, so no public URL/webhook is needed — ideal for development.*

| Lines | What it does and why |
|---|---|
| 1 | Docstring stating the polling choice and why. |
| 5-7 | Imports: `logging`, `time` (sleeps in the poll loops), `dataclass`. |
| 9 | `httpx` — Telegram's API is plain HTTP/JSON. |
| 11-12 | Imports `BotCore, Reply` (the contract) and `run_once` (reminders). |
| 14 | Module logger. |
| 17-25 | `Incoming` dataclass — Telegram's raw JSON normalised into one shape: `chat_id`, plus optionally `text`, or a downloadable `file_id` with its `caption`, `filename`, `mime`, and `is_document` (True for notice PDFs, False for photos). Core never sees Telegram JSON — it receives bytes and captions only. |
| 28-43 | `parse_update(update)` — pure function (heavily tested): extract the message and chat id (no chat id → `None`, e.g. edited messages/channel posts — ignored). A `photo` array → take the **last** (largest) size. A `document` → `is_document = not mime.startswith("image/")` (PDFs etc. go to ingest; image documents go to the photo flow). Plain `text` → text message. Anything else (sticker, voice, …) → `None` (ignored). |
| 46-53 | `TelegramTransport.__init__(token, core, client=None)` — refuses to start without a bot token (fail fast with a clear message). Builds the two API base URLs (bot API + file download API — note the token is embedded in both; never log these URLs). The optional `client` is the test seam, same pattern as `Backend`. |
| 55-56 | `send_text(chat_id, text)` — `sendMessage`, hard-capped at 4000 chars (Telegram's limit is 4096; core already splits at 1000). |
| 58-60 | `send_file(chat_id, data, filename, mime)` — uses **`sendDocument`, not `sendPhoto`**, on purpose: Telegram recompresses photos, which would break the portal's exact KB limits; documents are delivered byte-for-byte. |
| 62-64 | `_download(file_id)` — two-step Telegram file download: `getFile` resolves the id to a temporary path, then the file API returns the bytes. |
| 66-71 | `deliver(chat_id, replies)` — the transport's half of the `Reply` contract: for each reply, send text if present and file if present. |
| 73-91 | `handle(update)` — glue: parse → if undecodable, ignore. Document → `core.handle_document(...)`, deliver the instant ack, then **poll inline**: up to 30 × (sleep 2s → `poll_job`) and deliver as soon as a "ready"/"could not read" message appears. (While this polls, this update blocks the main loop — acceptable at current scale, see §11.) Image → `core.handle_image(...)`. Otherwise → `core.handle_text(...)`. Each result goes through `deliver()`. |
| 93-111 | `run(reminder_days=3)` — the infinite main loop: long-poll `getUpdates` with a 30s server-side timeout (Telegram holds the request open, so this is not busy-spinning); for each update, advance `offset` past it (so it's never processed twice) and `handle()` it inside try/except — one bad update is logged and skipped, never killing the bot. Once an hour, run deadline reminders. On a network error (`httpx.HTTPError`), log, sleep 5s, and keep going — the bot self-heals through network drops. |

### 4.8 `applypilot_bot/transports/whatsapp.py` — WhatsApp adapter (98 lines)

*Purpose: same contract as Telegram, but for Meta's WhatsApp Cloud API. Webhook-based: Meta pushes
messages to us, so this file is also a tiny web server (FastAPI). Marked EXPERIMENTAL at the top —
written from Meta's public docs; needs a public HTTPS URL and a live number to fully verify.*

| Lines | What it does and why |
|---|---|
| 1-7 | Docstring with two honest limitations: untested against a live number at writing time, and reminders need approved templates outside the 24h window (so this adapter only replies). |
| 11-12 | Imports: `hashlib`, `hmac` (signature maths), `httpx`, FastAPI pieces. |
| 14 | `from applypilot_bot.core import BotCore, Reply` — the same contract as Telegram. |
| 16 | `GRAPH = "https://graph.facebook.com/v20.0"` — Meta Graph API base (version pinned so an API upgrade is a deliberate change). |
| 19-24 | `valid_signature(app_secret, body, header)` — **the security gate**: Meta signs every webhook POST with HMAC-SHA256 of the raw body using your app secret. Recompute and compare with `hmac.compare_digest` (constant-time, so attackers can't guess by timing). Missing secret or malformed header → reject. Without this, anyone could POST fake "messages" and act as any user. |
| 27-32 | `extract_messages(payload)` — flattens Meta's nested `entry[] → changes[] → value.messages[]` structure into a simple list. Everything unhandled (statuses like "delivered" receipts live elsewhere in the payload) is naturally excluded. |
| 35-40 | `WhatsAppTransport.__init__(core, access_token, phone_number_id, verify_token, app_secret, client=None)` — stores the identifiers and creates an HTTP client with the `Authorization: Bearer` header pre-set for all Graph calls. |
| 42-43 | `send_text(to, text)` — `POST /{phone_id}/messages` with a text body, capped at 4000 chars. `to` is the user's phone number (WhatsApp's chat id). |
| 45-47 | `send_file(to, data, filename, mime)` — two calls: upload the bytes to `/{phone_id}/media` to get a media id, then send a `document` message referencing it. Document type (not image) for the same no-recompression reason as Telegram. |
| 49-51 | `_download(media_id)` — `GET /{media_id}` returns a temporary signed URL; fetch the bytes from it. |
| 53-58 | `deliver(to, replies)` — identical contract loop to Telegram's. |
| 60-76 | `handle_message(msg)` — per-message glue: `text` → `core.handle_text`; `image` → download + `core.handle_image` (with caption); `document` → download + `core.handle_document`, deliver the ack, then **one** immediate `poll_job` check (note the difference from Telegram: no polling loop here — Meta expects webhook handlers to return fast, so the "ready" message arrives on the user's next interaction or a future nudge; see §11). The sender's phone number (`from`) is the chat id. |
| 78-97 | `build_app()` — the FastAPI app with two routes. `GET /webhook` (lines 81-86): Meta's one-time verification — if `hub.mode=subscribe` and `hub.verify_token` matches yours (compared in constant time), echo back `hub.challenge`; otherwise 403. `POST /webhook` (lines 88-95): read the **raw** body (signature is over exact bytes — parsing first would break it), verify the signature or 403, then process every message and return `{"status": "ok"}`. |

### 4.9 `tests/test_core.py` — how the tests prove it works (159 lines)

*Purpose: 13 fast tests. No network, no Telegram, no backend — a fake backend implemented as an
in-memory HTTP handler, so these run in a fraction of a second and in CI.*

| Lines | What it does and why |
|---|---|
| 1-14 | Imports + `PNG = b"fakeimagebytes"` — tests never touch real images; the core only forwards bytes, so fake bytes are a faithful substitute. |
| 17-49 | `fake_backend(calls)` — a fake ApplyPilot backend as an `httpx.MockTransport` handler. It records every call (method, path, auth header) into `calls` so tests can assert *what the bot sent*, then behaves like the real API: `/bot/link` only accepts code `GOOD1234` **with** the right `X-Bot-Secret` and returns token `tok-123`; every other route 401s unless the header is `Bearer tok-123` (exactly like the real backend); canned answers for chat, deadlines (one "Army post"), notices (two: ids 3 and 4 — two matter for the ambiguity test), photo (returns base64 of `b"READY"`), job ingest (job 9 instantly `ready` with a summary line), profile GET/PUT, and eligibility for notice 3 (missing DOB) vs 4 (eligible). Unknown paths 404. |
| 52-57 | `core` fixture — builds a real `BotCore` wired to the fake backend and a `Store(":memory:")` (fresh empty DB per test), exposes the recorded `calls`, and hands it to each test. |
| 60-62 | Unlinked chat gets the link instructions **and** `core.calls == []` proves no backend call leaks before linking (privacy + security property). |
| 65-69 | Link flow: wrong code → "Could not link"; right code (lowercase, proving `.upper()`) → "Linked"; a question returns the canned answer; and the last recorded call proves the bot sent `Bearer tok-123`. |
| 72-74 | `/deadlines` formats the canned row into "Army post: 2026-11-14 (2 days left)". |
| 77-80 | Expired-token self-healing: a chat pre-linked with a bad token gets a 401 → core unlinks it and asks to re-link. |
| 83-88 | Photo flow end-to-end: caption `"photo 3 light blue"` → preview reply + file bytes `b"READY"`; then text `"yes"` → confirmation + the final file again. |
| 91-99 | Document flow: PDF bytes → "reading your notice" ack; `poll_job` → ready + "Last date" summary; the notice becomes the current one; a >5 MB file is rejected with the size message. |
| 102-109 | DOB flow: `/eligible` on notice 3 asks for DOB; replying `"05/08/2004"` saves it and clears `awaiting_dob`. |
| 112-116 | `split_text` on a long string produces multiple parts, each within ~1100 chars. |
| 119-122 | Ambiguity: image with no caption and two notices → asks "Which notice" and lists `#4 Bank PO`. |
| 125-128 | Reminders fire once per day: first `due_reminders` returns 1 pair, second call (same day) returns none. |
| 131-138 | Telegram `parse_update`: plain text; PDF document flagged `is_document`; photo picks the largest `file_id` and keeps the caption; stickers and edited messages are ignored (`None`). |
| 141-149 | WhatsApp signature: a correctly computed HMAC is accepted; wrong hash, empty secret, and missing header are all rejected. |
| 152-155 | WhatsApp payload flattening extracts the sender/text message and tolerates an empty payload. |

### 4.10 Small files

**`requirements.txt`** (4 lines) — the bot's complete dependency list:
`httpx` (all HTTP: backend, Telegram, Meta), `fastapi` + `uvicorn` (only for the WhatsApp webhook
server), `pytest` (tests). Deliberately tiny — the bot needs no AI, database-server, or image
libraries because the backend does that work. SQLite is in Python's standard library.

**`Dockerfile`** (9 lines) — how the bot is containerised:
`python:3.12-slim` base; no bytecode files + unbuffered logs (so container logs stream live);
working dir `/srv`; dependencies installed as their own layer (Docker caches them unless
`requirements.txt` changes); code copied in; a non-root `bot` user is created and used (never run
as root); `/srv/data` exists for the SQLite file; the start command is
`python -m applypilot_bot.main` — the same entry point as running locally.

**`__init__.py` files** (all empty) — their mere presence marks `applypilot_bot/`, `transports/`,
and `tests/` as Python packages so imports like `from applypilot_bot.core import BotCore` work.
Empty is normal and correct here.

**`.venv/`** — this machine's private Python environment (interpreter + installed packages).
Git-ignored; never edit by hand; recreate with `python -m venv .venv` + `pip install -r requirements.txt`.

**`.pytest_cache/`** — pytest's memory of the last run (which tests failed last, etc.). Safe to
delete; git-ignored.

**`data/bot.db`** — the live SQLite file created by `store.py` (git-ignored because it contains
user access tokens). Deleting it unlinks every chat and forgets state/reminders — users just
re-link. Back it up if your users would mind re-linking.

---

## 5. The bot's database tables

One SQLite file (`BOT_DB_PATH`, default `bot/data/bot.db`), three tables:

| Table | Columns | Meaning | Written by |
|---|---|---|---|
| `links` | `chat_id` (PK), `token` | "Telegram/WhatsApp chat X acts as ApplyPilot account whose backend token is T." This is the bot's entire login system. | `/link` success; deleted by `/unlink` or a 401 |
| `state` | `chat_id`, `key`, `value` (PK = chat+key) | Generic per-chat conversation memory. Keys in use: `notice_id` (current notice), `job_id` (ingest being tracked), `awaiting_dob` (`"1"` while waiting for a birth date), `pending_photo` (JSON stash of a photo awaiting yes/no). | core.py throughout |
| `reminders` | `chat_id`, `app_id`, `sent_on` (PK = all three) | "We already reminded this chat about this application on this date." The composite key makes duplicates impossible at the database level. | `reminders.py` |

There is deliberately **no** table for messages, questions, or answers: conversation content belongs
to the backend/account, not the bot, which keeps the bot's privacy surface tiny.

---

## 6. Every command and conversation the user can have

| User sends | Bot does | Backend calls |
|---|---|---|
| `/start`, `/help` | HELP text if linked, else welcome + link instructions | none |
| `/link CODE` | Exchanges the one-time website code for a token and stores it | `POST /bot/link` (bot secret) |
| `/unlink` | Deletes the link | none |
| `/deadlines` | Lists applications due in 14 days | `GET /applications/upcoming` |
| `/notices` | Lists up to 10 notices with `#id` | `GET /notices` |
| `/use 3` | Remembers notice 3 as the current one | none |
| `/eligible`, `/eligibility` | Eligibility verdict — or asks DOB first if missing | `GET /notices/{id}/eligibility` (+ profile if DOB follows) |
| `05/08/2004` (after being asked) | Validates and saves DOB to the profile | `GET /profile`, `PUT /profile` |
| Any other text | Forwards as a question about the current notice; long answers are split | `POST /assistant/chat` |
| A PDF/document | Instant ack, background ingest, then summary + key answers when ready | `POST /jobs/ingest`, `GET /jobs/{id}` |
| A photo, caption `photo 3 light blue` | Processes it (notice 3's rules, light-blue background), sends a preview | `POST /photo/process` |
| A photo, caption `signature 3` | Same, with signature rules | `POST /photo/process` |
| `yes` / `no` (after a preview) | Sends the final file as a document / discards it | none (already vaulted) |
| (automatic, Telegram) | Hourly: deadline reminders, once per application per day | `GET /applications/upcoming` |

Caption parsing cheat-sheet for photos: the word `sign…` anywhere → signature, else photo; the
first number → notice id; a colour name (`light blue`, `white`, …) or `#hex` → background colour.
No caption and exactly one notice → that notice is used automatically.

---

## 7. Configuration reference (`.env` variables)

Set these in the **repository-root `.env`** (the backend reads the same file; the bot reads the
process environment — when using Docker Compose they are injected for you).

| Variable | Required for | Meaning |
|---|---|---|
| `BOT_TRANSPORT` | always | `telegram` (default) or `whatsapp` |
| `BOT_SHARED_SECRET` | always | Must match the backend's value exactly; authorises `/bot/link` |
| `BACKEND_URL` | always | Backend base URL, default `http://localhost:8000` (no `/api/v1` — api_client adds it) |
| `BOT_DB_PATH` | optional | Bot SQLite path, default `./data/bot.db` |
| `TELEGRAM_BOT_TOKEN` | Telegram | From @BotFather. **Never hard-code it** (see warning at the top) |
| `WHATSAPP_ACCESS_TOKEN` | WhatsApp | Meta Cloud API token (Bearer) |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp | Business phone number ID (not the number itself) |
| `WHATSAPP_VERIFY_TOKEN` | WhatsApp | Any string you invent; echoed during webhook verification |
| `WHATSAPP_APP_SECRET` | WhatsApp | App secret used to verify webhook signatures |
| `REMINDER_DAYS` | optional | Reminder look-ahead window, default 3 days |

---

## 8. How to run it

Prerequisite: the backend is running (default `http://localhost:8000`) and `.env` holds matching
`BOT_SHARED_SECRET` values on both sides.

```powershell
# Telegram (no public URL needed)
cd bot
..\backend\.venv\Scripts\python.exe -m applypilot_bot.main

# WhatsApp (needs BOT_TRANSPORT=whatsapp in .env, plus a public HTTPS tunnel
# such as `ngrok http 8100` pointed at Meta's webhook configuration)
..\backend\.venv\Scripts\python.exe -m applypilot_bot.main   # serves the webhook on port 8100
```

First user step in either app: website → Profile → "Create link code" → send `/link CODE` to the bot.

Docker: `docker build -t applypilot-bot bot/` then run with the `.env` variables passed via
`--env-file` (the image starts `python -m applypilot_bot.main` as the non-root `bot` user).

---

## 9. How to test it

```powershell
cd bot
..\backend\.venv\Scripts\python.exe -m pytest tests -q
```

13 tests, all offline (fake backend via `httpx.MockTransport`, in-memory SQLite). They cover:
linking, question forwarding, deadlines, expired-token unlinking, the photo preview→confirm flow,
document ingest + size guard, the DOB conversation, message splitting, reminder de-duplication,
Telegram update parsing, and WhatsApp signature verification + payload parsing.

---

## 10. How to add a new feature (recipes)

**Add a new command, e.g. `/status`:**
1. In `core.py handle_text`, add a branch near the other commands (after the pending-state checks,
   so it can't hijack a DOB/photo reply): `if cmd == "/status": return [...]`.
2. If it needs data, add **one method** to `api_client.py Backend` (one `_send` call) — don't call
   `httpx` from core.
3. Add a test: extend `fake_backend` with the new path's canned response, then assert on
   `core.handle_text("1", "/status")`.
4. Mention the command in the `HELP` text.

**Add a new chat app, e.g. Signal:**
1. Create `transports/signal.py` with three abilities: receive (webhook or polling), normalise each
   message into calls to `core.handle_text / handle_image / handle_document`, and `deliver()`
   a `list[Reply]` (send text, send file bytes as a document).
2. Add a branch in `main.py` + any new settings in `config.py`.
3. Core, store, reminders, api_client: **unchanged**. That's the payoff of the layering.

**Add a new conversation step (multi-turn), e.g. asking "which category?":**
1. When you ask the question, `store.set_state(chat_id, "awaiting_category", "1")`.
2. At the **top** of `handle_text` (with the DOB/photo checks), handle and clear that state.
3. Validate strictly (like `_DOB_RE` + real-date check) — never save unvalidated free text.

**Rules that keep the design intact:**
- Core never imports a transport; transports never call the backend directly.
- New backend data = new `Backend` method + new fake-backend path in tests.
- Anything a user typed that gets persisted must be validated first.
- Errors from the backend are `BackendError` — let them bubble to `handle_text`'s `except`.

---

## 11. Known limitations and things to improve

1. **Hard-coded Telegram token default** in `config.py` line 13 — remove the fallback, revoke and
   rotate the token via @BotFather (see the warning at the top). Settings should fail fast if the
   token is missing in Telegram mode (telegram.py already raises if it's empty).
2. **Telegram ingest polling blocks the main loop** (telegram.py `handle`): while polling a job
   ( up to ~60s), other users' messages wait. Fine for a few users; the upgrade path is to record
   `(chat_id, job_id)` and check jobs inside the hourly/minute tick of `run()` instead.
3. **WhatsApp only polls the job once** (whatsapp.py `handle_message`): the "notice ready" summary
   may not arrive until the user writes again. Fix together with (2): a periodic job-checker that
   can push via `send_text` (allowed within the 24h window after the user's upload).
4. **Photo stash can linger:** if the user sends a question instead of yes/no, `pending_photo`
   stays set and a later stray "yes" (even in a new conversation) would confirm the old photo.
   Upgrade: store a timestamp in the stash and expire it, and clear it when a new photo/document
   arrives.
5. **`split_text` edge case:** a single sentence longer than the limit is sent whole (transports
   cap at 4000, so it still delivers, just as one longer message).
6. **`handle_document`'s `caption` parameter is unused** — reserved for future hints (e.g. naming
   the notice). Either use it or drop it when next touching that function.
7. **WhatsApp is unverified against a live number** and reminder *pushes* need Meta-approved
   message templates — budget time for Meta app review before promising reminders on WhatsApp.
8. **Secrets in `data/bot.db`:** stored tokens are plaintext SQLite. Acceptable locally; for a
   hosted deployment, restrict file permissions or move links server-side.
9. **`_confirm_photo`'s unused `token` parameter** and telegram.py's inline `import time as _time`
   (already imported at module top) — small clean-ups for the next refactor pass.

---

## 12. Glossary

- **Transport** — the per-app adapter file (telegram.py / whatsapp.py). Reads and writes messages; knows no rules.
- **Core (`BotCore`)** — the shared brain in core.py. All rules and conversations.
- **Reply** — the core's output unit: optional text + optional `(bytes, filename, mime)` file.
- **Link / linking** — connecting a chat to an ApplyPilot account via a one-time code from the website; afterwards the bot holds a per-chat access token.
- **Current notice** — the notice follow-up questions refer to: set by `/use`, by a finished ingest, or auto-chosen when the user has exactly one.
- **State** — one row in the `state` table remembering which conversation step a chat is in (`awaiting_dob`, `pending_photo`, …).
- **Background ingest** — the backend reads a PDF as a job (`queued→reading→indexing→ready/failed`) so the bot can reply instantly and notify when done.
- **Long polling** — Telegram mode: the bot keeps an open request to Telegram instead of exposing a webhook.
- **Webhook** — WhatsApp mode: Meta sends HTTP POSTs to our FastAPI app; authenticity is proven by the HMAC signature check.
