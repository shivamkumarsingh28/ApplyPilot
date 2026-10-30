# Getting started

This guide takes you from nothing to a running ApplyPilot. Follow the steps in order. Each step says how to check that it worked.

## 1. What you need

- Python 3.11 or newer (`python3 --version`)
- Node.js 20 or newer (`node --version`)
- Git
- Optional: Docker, Ollama, a Meta API key, Chrome

## 2. Get the code and make your settings file

```bash
git clone <your-repo-url> applypilot
cd applypilot
python3 scripts/setup_env.py
```

This creates a file called `.env`. It holds your settings and random secret keys. **Never share it or commit it to Git.** (It is already in `.gitignore`.)

## 3. Run the backend (the API)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Check: open http://localhost:8000/api/v1/health. You should see `"status": "ok"`.
Interactive API docs are at http://localhost:8000/docs.

Run the tests: `python -m pytest -q` (you should see all tests pass).

## 4. Run the website

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Check: open http://localhost:3000. You should see the sign-in page. Create an account.

## 5. Try it with the sample notice

1. Go to **Profile** and fill your date of birth, qualification, and category. Save.
2. Go to **Notices**, paste the text of `samples/sample_notice.txt`, and press **Read this notice**.
3. Ask: "What is the application fee?" and "Is there a physical test?"
4. Look at "Am I eligible?" and "Is this notice safe?".
5. Go to **Photo studio**, pick the notice, and upload any selfie. Download the result.

## 6. Use a real AI model (optional)

### Option A: Llama on your computer (free)

1. Install Ollama from https://ollama.com
2. `ollama pull llama3.2`
3. In `.env` set:
   ```
   LLM_PROVIDER=llama_local
   OLLAMA_MODEL=llama3.2
   ```
4. Restart the backend. `/api/v1/health` now shows `"provider": "llama_local"`.

For scanned notices you need a model that can see images: `ollama pull llama3.2-vision` and set `OLLAMA_VISION_MODEL=llama3.2-vision`.

### Option B: Meta Model API (production)

1. Get a key from https://developer.meta.com (Meta Model API).
2. In `.env` set:
   ```
   LLM_PROVIDER=meta
   META_API_KEY=your-key
   ```
3. Restart the backend.

## 7. Install the browser extension

See [EXTENSION.md](EXTENSION.md). Short version: Chrome, `chrome://extensions`, turn on Developer mode, **Load unpacked**, choose the `extension` folder. Open `samples/sample_form.html` in a tab and click the ApplyPilot icon.

## 8. Run the Telegram bot (optional)

See [BOT.md](BOT.md). Short version: make a bot with @BotFather, put the token in `.env`, run `python -m applypilot_bot.main` inside `bot/`.

## 9. Run everything with Docker (optional)

```bash
docker compose up --build
```

Then open http://localhost:3000.

## Common problems

| Problem | Fix |
|---|---|
| Website says "Failed to fetch" | The backend is not running, or `NEXT_PUBLIC_API_URL` is wrong. |
| "This looks like a scanned document" | You use `mock`. Set a model with vision (see step 6). |
| Everything returns 429 | You hit the rate limit. Wait one minute. |
| Docker backend exits with ENCRYPTION_KEY error | Run `python3 scripts/setup_env.py` and try again. |
