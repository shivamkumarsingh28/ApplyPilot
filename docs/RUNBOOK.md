# Runbook — set up, run, and verify ApplyPilot

Three ways to run, in order of effort. Everything works with **no AI key**
(`LLM_PROVIDER=mock` is the default); add a model later without code changes.

## Option A — local development (recommended first run)

You need Python 3.11+ and Node 20+.

```powershell
# Windows PowerShell — from the repo root
py scripts\setup_env.py                      # creates .env with random secrets

# Terminal 1: API
cd backend
py -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt          # note: opencv-python-headless is pinned <5.0
python -m pytest -q                          # expect: 84 passed
uvicorn app.main:app --reload --port 8000    # http://localhost:8000/docs

# Terminal 2: website
cd frontend
npm install
npm run dev                                  # http://localhost:3000

# Terminal 3 (optional): bot + extension tests
cd bot ; python -m pytest -q                 # expect: 10 passed
cd ..\extension ; npm install ; npm test     # expect: 4 passed
```

macOS/Linux: same commands with `python3`, `source .venv/bin/activate`, and
forward slashes. Or use the Makefile: `make setup`, `make dev-backend`,
`make dev-frontend`, `make test`.

### First-run smoke test (2 minutes)
1. Open http://localhost:3000 → register an account.
2. **Profile**: add date of birth, qualification `10th`, percentage, category. Save.
3. **Notices**: paste the contents of `samples/sample_notice.txt` → *Read this notice*.
   Expect: last date 14 Nov 2026, fee ₹250, scam level **low**.
4. Ask *"Is there a physical test?"* (answer cites the page) and *"Am I eligible?"*.
5. **Print checklist** — one printable page. Dashboard → **Add deadlines to my
   calendar (.ics)** downloads reminders.
6. **Photo studio**: upload any selfie for that notice → 200×230 px, 20–50 KB.

## Option B — Docker (website + API + database)

```bash
make setup
docker compose up --build                    # web :3000, API :8000/docs
docker compose --profile bot up --build      # + Telegram bot
docker compose --profile local-llm up --build && make pull-llama   # + local Llama
```

## Option C — add a real Meta model

| Goal | `.env` settings |
|---|---|
| Free, on your laptop | `LLM_PROVIDER=llama_local`, `OLLAMA_MODEL=llama3.2` (run `ollama pull llama3.2` first; add `llama3.2-vision` + `OLLAMA_VISION_MODEL` for scanned notices) |
| Production (Meta Model API / Muse Spark) | `LLM_PROVIDER=meta`, `META_API_KEY=...`, `META_MODEL=muse-spark-1.3` |
| Any OpenAI-compatible host | `LLM_PROVIDER=openai_compat`, `OPENAI_COMPAT_BASE/KEY/MODEL` |
| SAM 3.1 background removal | `SEGMENTER=meta_sam`, `SAM_ENDPOINT=...` (default `opencv` needs nothing) |

Restart the backend after changing `.env`. `GET /api/v1/health` shows the
active provider. Details: [MODELS.md](MODELS.md).

## Chrome extension

Chrome → `chrome://extensions` → Developer mode → **Load unpacked** → choose
`extension/`. Open `samples/sample_form.html`, click the ApplyPilot icon,
sign in with the same account, **Scan**, review, **Fill**. It never submits
and never fills passwords/ID numbers. See [EXTENSION.md](EXTENSION.md).

## Telegram bot

Create a bot with @BotFather, put `TELEGRAM_BOT_TOKEN` in `.env`, then
`cd bot && python -m applypilot_bot.main`. In the web app, Profile → *Create
link code*, then send `/link CODE` to the bot. See [BOT.md](BOT.md).

## Verify everything (the test suites)

| Suite | Command | Expected |
|---|---|---|
| Backend | `cd backend && python -m pytest -q` | 84 passed |
| Bot | `cd bot && python -m pytest -q` | 10 passed |
| Extension | `cd extension && npm test` | 4 passed |
| Extension syntax | `cd extension && npm run check` | no errors |
| Frontend types | `cd frontend && npm run lint` | no errors |
| Frontend build | `cd frontend && npm run build` | build succeeds |
| All-in-one | `make test` | all of the above |

## Troubleshooting

| Symptom | Fix |
|---|---|
| `python` opens the Microsoft Store (Windows) | Use `py` or the venv interpreter (`.venv\Scripts\python.exe`) |
| Photo tests fail with `cv2 has no attribute CascadeClassifier` | OpenCV 5 is installed. `pip install "opencv-python-headless<5.0"` (pinned in `requirements.txt`); the code also falls back to YuNet on v5 |
| Website says "Failed to fetch" | Backend not running, or `NEXT_PUBLIC_API_URL` wrong |
| "This looks like a scanned document" | Set a vision model (Option C) |
| Everything returns 429 | Rate limit — wait one minute |
| Docker backend exits with ENCRYPTION_KEY error | Run `python scripts/setup_env.py` first |
| Extension cannot reach the API | API must run on `http://localhost:8000` (manifest host permission), or grant the optional host permission for your deployed URL |
