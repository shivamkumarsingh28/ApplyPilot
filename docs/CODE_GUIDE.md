# Code guide — file by file, and how to change things

Read [ARCHITECTURE.md](ARCHITECTURE.md) first for the big picture. This guide
lists every source file, what it does, and the exact place to change common
things. The rule everywhere: **routes handle HTTP, services handle logic.**
To change behaviour, edit a service and its test; routes rarely need edits.

## Backend (`backend/app/`)

### Startup and configuration
| File | What it does | Change here if… |
|---|---|---|
| `main.py` | `create_app()` builds FastAPI: CORS (incl. `chrome-extension://`), security headers, handlers mapping `UnreadableDocument`→422 and `LLMError`→502, mounts routes under `/api/v1` | you add global middleware or error types |
| `__init__.py` | Package version string | you release a version |
| `core/config.py` | All settings from `.env` (`Settings`), cached `get_settings()` | you add a setting (also add it to `.env.example`) |
| `core/security.py` | bcrypt password hashing, JWT create/verify | token lifetime, password rules |
| `core/crypto.py` | Fernet encryption for profiles and files | key handling |
| `core/ratelimit.py` | In-memory sliding-window limiter; `limit("ai")` etc. | rate-limit numbers (values live in `.env`) |
| `core/uploads.py` | Sniffs real file type from bytes, compares with claimed type | allowed file types |

### Database (`db/`)
| File | What it does |
|---|---|
| `base.py` | SQLAlchemy `DeclarativeBase` |
| `models.py` | Tables: `User`, `Profile` (encrypted blob), `Document` (metadata only), `Notice` + `NoticeChunk` (text + embedding), `Application`, `BotLink`, `AuditLog`. Add a column here + a field in the matching schema to store new data. There are no migrations yet — deleting `data/applypilot.db` recreates tables in dev. |
| `session.py` | Engine/session factory, `init_db()`, `reset_engine()` (tests) |

### HTTP layer (`api/`)
| File | What it does |
|---|---|
| `deps.py` | `get_current_user` (JWT → active user), `get_owned` (404 for other users' rows — this is the isolation rule), bot-secret check |
| `router.py` | Includes every route module. **Register new route files here.** |
| `routes/auth.py` | `POST /auth/register` (201, 409 on duplicate), `/login`, `GET /auth/me` |
| `routes/profile.py` | `GET/PUT /profile` — decrypts/encrypts via `profile_store` |
| `routes/documents.py` | Vault: upload (type sniffed, ≤10 MB), list, download, delete; `store_document()` is reused by Photo Studio |
| `routes/notices.py` | Create (file or pasted text → extract → scam check → RAG ingest → tracker row), list (with `?scam_level=` filter), get, delete, `POST /{id}/ask`, `GET /{id}/eligibility`, `GET /{id}/readiness` |
| `routes/photo.py` | `POST /photo/process`: spec from a notice or manual overrides → `photo_studio` → optional save to vault |
| `routes/forms.py` | `POST /forms/map` → `form_mapper.map_fields` |
| `routes/applications.py` | Tracker CRUD + `GET /upcoming` (bot reminders) + `GET /summary` (dashboard: counts, next deadline, time-saved heuristic) |
| `routes/export.py` | `GET /notices/{id}/checklist` (printable HTML), `GET /applications/calendar.ics` (7/3/1-day reminders). Both owner-checked like every other route |
| `routes/assistant.py` | `POST /assistant/chat` → agents runner |
| `routes/bot.py` | `POST /bot/link-code` (user) and `/bot/link` (bot secret header, one-time code) |
| `routes/admin.py` | Admin-only: users, stats, audit log |
| `routes/health.py` | `GET /health` — also reports the active LLM provider |

### Schemas (`schemas/`) — request/response shapes
`auth.py`, `profile.py` (`ProfileData`, `extra="forbid"`, validates DOB/category;
ID-number fields are deliberately rejected), `document.py` (`DOCUMENT_KINDS`),
`notice.py`, `application.py` (status enum), `forms.py`. **Validation rules
live here** — e.g. to allow a new profile field, add it to `ProfileData`,
teach `form_mapper.SYNONYMS` its labels, and extend the profile page.

### Services (`services/`) — where the logic lives
| File | What it does | Change here if… |
|---|---|---|
| `extraction.py` | Notice text → structured facts. `rule_extract` (regex) first, `llm_extract` fills gaps, disagreements land in `needs_review`. `DOC_KEYWORDS`, `STAGE_KEYWORDS`, `QUAL_ORDER` at the top | a notice phrases something new ("Last date", age, fee, a document kind, a stage) — add the keyword/pattern and a test in `tests/test_extraction.py` |
| `eligibility.py` | Deterministic verdict: deadline, age (exact years/months/days + category relaxations), qualification order, min marks, gender. Never uses the model | an eligibility rule changes |
| `readiness.py` | Required documents vs vault kinds → percent, have/missing, days left. `LABELS` names each document kind | a document kind is added |
| `rag.py` + `chunking.py` + `embeddings.py` | Page-aware chunks + vectors; `answer()` returns citations or `not_found` — it never invents a date/fee | chunk size, embedding provider |
| `scam_check.py` | Fake-notice heuristics → score/level/reasons | a new fraud pattern appears |
| `guardrails.py` | Input/output safety: injection attempts, off-topic, other users' data | a new abuse pattern appears |
| `photo_studio.py` | `process_photo`: face detect → crop → segment → resize → fit KB range (binary-search quality, pads JPEG to minimum). `_detect_face` uses Haar on OpenCV <5 and YuNet on 5+. `_detect_face` returning `None` falls back to centre crop with a warning | photo rules, background colours (`BACKGROUNDS`) |
| `segmenter.py` | Foreground mask: OpenCV GrabCut or SAM 3.1 HTTP endpoint (`SEGMENTER`) | segmentation backend |
| `form_mapper.py` | Field descriptors → profile values. Order: autocomplete attr → phrase match (`SYNONYMS`) → fuzzy → optional model suggestion (always review). `SKIP_WORDS`/`SKIP_TYPES` are never filled | a form label is not recognised — add the phrase to `SYNONYMS` |
| `export.py` | `checklist_html()` (escaped, printable) and `ics_calendar()` (3 VEVENTs per deadline) | checklist content, reminder days |
| `pdf_text.py` | PDF/image/text → page texts; scanned input needs a vision model, else `UnreadableDocument` | new input formats |
| `profile_store.py`, `storage.py`, `audit.py` | Encrypted profile blob; encrypted files on disk; metadata-only audit log | storage backend |
| `llm/base.py` | Provider interface (`chat`, `offline`) | a new provider capability |
| `llm/mock.py` | Offline provider: services use rule-based paths | — |
| `llm/openai_compat.py` | One HTTP client used by `meta`, `llama_local` and `openai_compat` | request/response format of a host |
| `llm/factory.py` | Builds the provider named by `LLM_PROVIDER` | provider selection |
| `agents/supervisor.py` | Picks ONE specialist agent (model or keyword router) | routing rules |
| `agents/agents.py` | The four agents and their allowed tools | an agent's job |
| `agents/tools.py` | Nine tools, each scoped to the calling user (`ToolContext`) | a new assistant capability |
| `agents/runner.py` | Runs one agent turn: choose tool → call → answer | tool-calling loop |
| `agents/assistant.py` | One chat turn: guardrails → supervisor → agent → guardrails | chat flow |

### Tests (`backend/tests/`)
`conftest.py` builds a throwaway SQLite DB + mock LLM and the sample-photo
helpers. Suites mirror the services (`test_extraction.py`, `test_eligibility.py`,
`test_photo_studio.py`, `test_form_mapper.py`, `test_scam_check.py`,
`test_guardrails.py`, `test_agents.py`, `test_llm_providers.py`,
`test_security.py`), plus `test_api_flow.py` (end-to-end) and
`test_export_features.py` (checklist, calendar, summary, scam filter).
Run: `cd backend && python -m pytest -q` → currently **84 passed**.

## Frontend (`frontend/`)

| File | What it does |
|---|---|
| `lib/api.ts` | Fetch wrapper: bearer token from `localStorage`, JSON errors as `ApiError`, 401 → `/login`, `api.blob()` for downloads (checklist, calendar, documents) |
| `lib/types.ts` | TypeScript mirrors of the API schemas (`Structured`, `Eligibility`, `Readiness`, `Summary`, …). **When you add an API field, add it here.** |
| `app/page.tsx` | Dashboard: "At a glance" summary card (+ .ics download), deadlines, recent notices |
| `app/notices/page.tsx` | Upload/paste a notice → redirects to its page |
| `app/notices/[id]/page.tsx` | Key facts, scam report, eligibility, readiness, "Ask this notice" chat, Print checklist, delete |
| `app/photo/page.tsx` | Photo/signature studio UI against a notice spec or manual size |
| `app/vault/page.tsx`, `app/tracker/page.tsx`, `app/profile/page.tsx`, `app/assistant/page.tsx`, `app/login/page.tsx` | Vault CRUD, tracker CRUD, profile form, assistant chat, sign-in |
| `components/AuthGate.tsx`, `Nav.tsx`, `ui.tsx` | Token gate, sidebar, shared `Card`/`Badge`/`Empty`/`ErrorText` |

Checks: `npm run lint` (tsc) and `npm run build` must pass.

## Extension (`extension/`)

`manifest.json` (MV3, `activeTab`+`scripting`+`storage`, never auto-submits) →
`popup.html`/`popup.js` (sign in, scan, review, fill) → `content.js` bridges
page messages → `lib/fieldScanner.js` (describes every fillable control;
skips password/file/checkbox, groups radios — pure DOM, unit-tested with
jsdom in `tests/scanner.test.js`) → `lib/filler.js` (writes reviewed values).
A field that will not fill is almost always a scanner label problem
(`labelFor`) or a missing phrase in backend `SYNONYMS`.

## Bot (`bot/applypilot_bot/`)

`core.py` holds all chat rules (`handle_text`, `handle_image` → `Reply`s);
transports only move messages: `transports/telegram.py` (long polling),
`transports/whatsapp.py` (Cloud API, signature-verified). `api_client.py`
calls the backend with the linked user's token; `store.py` links chat ↔
account and remembers sent reminders; `reminders.py` sends one reminder per
application per day. Tests: `bot/tests/test_core.py` (mock HTTP backend).

## Recipes

- **Add an API endpoint**: service function + test → route in `api/routes/` →
  register in `api/router.py` → add the type to `frontend/lib/types.ts` →
  regenerate `docs/API.md` from `/openapi.json`.
- **Support a new notice wording**: pattern/keyword in `extraction.py` →
  case in `tests/test_extraction.py` → run the backend suite.
- **Change the Meta model**: `.env` only — `LLM_PROVIDER=meta`,
  `META_MODEL=...`. No code change (see `docs/MODELS.md`).
- **Add a profile field**: `schemas/profile.py` → `form_mapper.SYNONYMS` →
  `frontend/app/profile/page.tsx` → tests.
