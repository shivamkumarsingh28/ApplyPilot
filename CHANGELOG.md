# Changelog

## Hotfix: existing-DB crash + SAM 404 (unreleased)

- **Fixed `POST /photo/process` 500 `table documents has no column named is_original`**: Phase 2 columns were added to the model but `create_all` never alters existing tables. [session.py](backend/app/db/session.py) `init_db()` now adds missing `documents` columns (`is_original`, `original_id`, `application_id`, `notice_id`, `app_ref`) idempotently on startup — existing data preserved. Regression tests in `tests/test_db_migration.py` (old-schema DB + the exact photo-vault path that crashed). Live DB migrated; backup at `backend/data/applypilot.db.bak-phase2`.
- **Fixed SAM 404 noise**: settings loaded `.env` relative to the working directory, but the documented run command cds into `backend/` where the repo-root `.env` is invisible — config silently used the built-in SAM default (`https://api.meta.ai/v1` → 404, GrabCut fallback). [config.py](backend/app/core/config.py) now resolves `.env` from the repo root. Your `.env` already has `SEGMENTER=opencv`, so **no SAM credential is needed**; photos use OpenCV. Only obtain a SAM endpoint if you want hosted segmentation (see guide in the fix report).

## Fixes + UI upgrade (unreleased)

- **Fixed (found by running everything):** dev CORS rejected the web app on any port other than the one in `.env` (`CORS_ORIGINS=http://localhost:3001`) — the API now allows any `localhost`/`127.0.0.1` origin outside production, production stays locked to `CORS_ORIGINS` (regression test in `tests/test_cors_theme.py`); React 18 deprecated warning under Next 16 → upgraded to React 19; 3 pre-existing ruff errors (unused imports/vars); bot test fake-backend updated for new endpoints
- **Verified live:** backend 93 tests, bot 13, extension 6, ruff clean, `next build` clean (no more React deprecation warning), live smoke on fresh ports (register → sync notice → background job `ready` with key answers → paraphrase ask → assistant chat), browser check of login/register, dark mode, and chat page
- **UI:** dark/light mode toggle (login + nav), persisted in `localStorage`, follows system preference, no flash on load; gradient theme, sticky glass nav with pill links, focus-visible states, reduced-motion support
- **Chatbot interface:** avatar bubbles, timestamps, suggested-question chips, typing indicator, Enter-to-send, Copy per answer, Clear chat, tool/agent badges; Photo studio gains background-colour picker (presets + any name/`#hex` + colour swatch, portal rule still wins)

## Phase 2 (unreleased)

- Background ingest jobs (`queued→reading→indexing→ready/failed`) with per-step timings; Telegram/WhatsApp PDF ingest with instant ack + ready notification, notice selection (`/use`, `/notices`), DOB prompt + `/eligible`, long-message splitting
- Retrieval: top-12 → rerank → top-3, heading weight, paraphrase synonyms, strict sourced prompt, (notice, question) answer cache; 30-question evaluation harness (`backend/scripts/evaluate.py`, offline score 29/30)
- Vault: originals vs application copies with `APP-####` references, 5 MB / 50 MB quotas (configurable), guarded original deletion; photo output saved as a copy
- Photo by chat: any colour name or `#hex`, portal-rule override guard, preview → "yes" confirm, sent as document
- Login: Google/GitHub/LinkedIn OAuth (credential-gated, `oauth_accounts` linking) alongside email+password; enabled providers listed at `/auth/providers`
- Web search via Brave or Tavily (never Google Custom Search) with trusted-domain allowlist for "save as notice"
- Extension: vault file list, file-field detection, attach via `files` + `change`, downloads fallback; never submits
- Kept (measured better at current scale): DB-thread job queue over Redis/RQ, JSON hash embeddings over pgvector (per-notice corpora are dozens of chunks), SAM adapter with OpenCV fallback

## 0.1.0 (unreleased)

- First version: API, website, extension, Telegram bot, WhatsApp adapter (experimental)
- Model providers: mock, llama_local (Ollama), meta (Muse), openai_compat
- Roles, audit log, guardrails, rate limits, supervisor and agents
- Docker Compose, CI, documentation
