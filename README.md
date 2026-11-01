# ApplyPilot

**Apply for jobs, exams and admissions with less stress.**

Many young people lose chances because of paperwork: long notices nobody reads, photos that the portal rejects, and the same form typed again and again. ApplyPilot fixes this in one place.

| What you do | What ApplyPilot does |
|---|---|
| Upload a job or admission notice (PDF, photo, or text) | Reads it, shows the key facts, and checks if it looks fake |
| Ask "Am I eligible?" | Checks your profile against the rules and explains each check |
| Ask any question about the notice | Answers from the notice only, and tells you the page |
| Upload a selfie and a signature | Resizes them to the exact pixels, KB and background the portal wants |
| Open the application form | The browser extension fills it from your profile. You review, then submit. |
| Chat on Telegram | Ask questions, fix photos, get deadline reminders |

## Who is this for?

Students and young workers everywhere. The first examples use Indian government job forms, but nothing in the code is limited to one country.

## Quick start (about 5 minutes, no AI model needed)

You need Python 3.11+ and Node 20+.

```bash
git clone <your-repo-url> applypilot && cd applypilot
python3 scripts/setup_env.py            # creates .env with random secrets

# Terminal 1: the API
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2: the website
cd frontend && npm install && npm run dev
```

Open http://localhost:3000, create an account, then add the sample notice from `samples/sample_notice.txt`.

The default is the **Meta Model API** (`LLM_PROVIDER=meta`, `META_MODEL=muse-spark-1.3`) for development, testing and production. If `META_API_KEY` is empty the app falls back to the offline mock with a warning, so tests and a first look still work. With `mock`, answers are copied from the notice text.

**Confirmed model setup:** chat/extraction/vision = Meta `muse-spark-1.3`. Meta's API has no embeddings endpoint, so embeddings use a separate embedding model (`EMBEDDING_MODEL` on an OpenAI-compatible endpoint, e.g. a hosted multilingual embedder or Ollama `nomic-embed-text`); unset = offline hash vectors. `llama_local` is an optional backup only, not the default.

## Choose your AI model

Set `LLM_PROVIDER` in `.env`:

| Value | What it is | When to use |
|---|---|---|
| `meta` | Meta Model API (Muse Spark 1.3). Needs `META_API_KEY`. | **Default: development, testing, production** |
| `llama_local` | A Meta Llama model on your own computer (through Ollama). Free. | Optional backup only |
| `mock` | No model. Fixed rules only. | First look, tests, CI |
| `openai_compat` | Any OpenAI-style server (OpenAI, Baseten, Fireworks, Modal, vLLM) | If you prefer another host |

Switching is only a setting. No code changes. Details: [docs/MODELS.md](docs/MODELS.md).

**Shared notices:** a public notice is processed once. If another user uploads the same PDF, they are linked to the existing copy instantly (no re-reading/chunking/embedding) and get their own tracker entry and eligibility from their own profile. Files that look personal are never shared.

## Run everything with Docker

```bash
make setup                                   # creates .env
docker compose up --build                    # website, API, database
docker compose --profile bot up --build      # also start the Telegram bot
docker compose --profile local-llm up --build && make pull-llama   # also run Llama locally
```

Website: http://localhost:3000  API docs: http://localhost:8000/docs

## What is inside

```
applypilot/
├── backend/      The API (Python, FastAPI). All the smart parts live here.
├── frontend/     The website (Next.js, TypeScript).
├── extension/    The Chrome extension that fills forms.
├── bot/          The Telegram bot, and a WhatsApp adapter.
├── docs/         Guides (start here: GETTING_STARTED.md).
├── samples/      A fictional notice and a fake form for testing.
├── scripts/      Helper scripts.
└── docker-compose.yml
```

## Safety and privacy in short

- Every user sees **only their own data**. Even admins cannot read other users' notices, profiles or files.
- Files and profiles are **encrypted** before they are saved.
- The assistant has **guardrails**: it refuses attacks, off-topic requests and questions about other users.
- A **supervisor** chooses a specialist agent, and each agent can use only its own small list of tools.
- The extension **never submits a form**, and never fills passwords, captchas or ID numbers.

Read more: [docs/SECURITY.md](docs/SECURITY.md).

## Documentation

| Guide | For |
|---|---|
| [Getting started](docs/GETTING_STARTED.md) | Set up step by step |
| [Runbook](docs/RUNBOOK.md) | Set up, run, verify, troubleshoot |
| [Features and roadmap](docs/FEATURES_AND_ROADMAP.md) | Full use case, wireframe map, next features |
| [Code guide](docs/CODE_GUIDE.md) | Every file explained, and where to change things |
| [v1 problem fixes](docs/issues/v1-problem-fixes/README.md) | Every issue found and fixed in v1, folder/file/line-wise |
| [Architecture](docs/ARCHITECTURE.md) | How the pieces fit together |
| [Models](docs/MODELS.md) | Llama, Meta Muse, and how to switch |
| [Agents](docs/AGENTS.md) | Supervisor, agents, tools |
| [Security](docs/SECURITY.md) | Every protection, and what is still your job |
| [Extension](docs/EXTENSION.md) and [Bot](docs/BOT.md) | Install and use |
| [API](docs/API.md) | All endpoints |
| [Deployment](docs/DEPLOYMENT.md) | Going live |
| [MCP plan](docs/MCP_PLAN.md) | A proposal for the next phase |
| [Roadmap](docs/ROADMAP.md) | What is done and what is next |
| [Contributing](CONTRIBUTING.md) | How to change the code |

## Honest status

Tested here: the API (84 automated tests using the offline model and simulated model servers), the bot logic (10 tests), the extension's field scanner and filler (4 tests in a simulated browser), and the website's type check and production build. See [docs/RUNBOOK.md](docs/RUNBOOK.md) to reproduce.

**Not yet tested against the real thing:** the Meta Model API with a live key, a running Ollama, a live Telegram or WhatsApp account, Docker Compose, PostgreSQL, SAM 3.1, and face detection on real photos. The code for these is written and unit-tested with fakes, but run it yourself before you rely on it. See [docs/ROADMAP.md](docs/ROADMAP.md).

## License

MIT. See [LICENSE](LICENSE).
