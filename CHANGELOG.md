# Changelog

## Extension: in-popup PDF preview (unreleased)

- **Problem:** image previews worked in the popup, but PDF preview opened a new browser tab — the user was dragged away from the half-filled form and lost their place.
- **Fix:** PDFs now render **page 1 to a canvas inside the popup** (`lib/pdfPreview.js`, vendored pdf.js 4.2.67 module + worker in `lib/pdfjs/`, loaded lazily only when a PDF preview is requested). No tab is ever opened for preview. Other file types say so plainly and point to Attach + check on the page.
- Manifest CSP allows local module scripts + `wasm-unsafe-eval` (pdf.js requirement); blob URLs are revoked on re-preview/choice change.
- Verified: 13 extension tests (incl. a guard that popup.js contains no `chrome.tabs.create`); live browser render of a test PDF — page 1 drawn at 200×283 in place with the correct title text visible.

## Extension: user-in-between matching (unreleased)

- **Real-user rule:** a student mid-form must never be handed a forced wrong guess. The matcher now returns confidence — `exact` (single kind+type winner) is pre-selected; `possible` (tie, or generic field like "certificate") pre-selects nothing, shows a "Please choose" badge, and Attach stays disabled until the user picks. Attach-all only attaches exact matches.
- Every field card shows a *Why* line (vault tag, type, application-copy), file sizes, a Preview (image thumbnail; PDFs open in a tab), and a size warning parsed from the field hint ("20 KB to 50 KB" / "max 200KB" / "up to 1 MB").
- After attach, the page itself shows "✓ ApplyPilot: filename" next to the field (plus the green outline), so the user verifies on the form, not just in the popup.
- Choices are remembered per website + field and pre-selected next visit.
- Verified: extension tests 11/11; live browser run on the sample form — photo = exact/suggested, certificate + tied signatures = possible/no suggestion, size warning for an 88 KB file in a 50 KB field, visible ✓ label after attach.

## Extension: vault-to-form attach enhancement (unreleased)

- **Approach:** scan the page's file fields → classify each (photo/signature/certificate/…) → match vault documents (kind + `accept` type, application copies preferred) → attach on click via `DataTransfer` (browsers forbid setting file-input values directly) → green outline + status; the form is never submitted and files are fetched only at click time.
- `fieldScanner`: file fields now carry `kind`, `hint` (nearby size/format text) and `customUpload` (hidden inputs behind custom Upload widgets are reported, not skipped).
- New `lib/vaultMatcher.js` (pure, node-tested): one suggested document per field, incompatible types excluded.
- Popup rebuilt for documents: one card per file field with pre-selected suggestion, dropdown to change, per-field attach status, "Attach all suggested", clearer blocked-site fallback message.
- Verified: extension tests 9/9, syntax checks pass, and a live browser run on `samples/sample_form.html` attached photo/signature/certificate correctly (1 file on each input).

## Phase V2: Meta default, RAG/extraction quality, shared notices (unreleased)

- **Model (confirmed):** default is now the Meta Model API — `LLM_PROVIDER=meta`, `META_MODEL=muse-spark-1.3` — for development, testing and production. `llama_local` is an optional backup only. Empty `META_API_KEY` falls back to the offline mock with a warning (tests never crash). Meta has no embeddings endpoint, so embeddings are a separate model (`EMBEDDING_BASE`/`EMBEDDING_MODEL` on an OpenAI-compatible endpoint); unset = offline hash vectors. The model name is stored on every chunk.
- **Chunking:** chunks no longer cross section headings; heading + page + a larger parent block are stored per chunk, table rows stay together — a rule and its exception now retrieve together.
- **RAG:** short notices are answered from the whole document (no missed chunk); every date/number in a model answer is verified against the source text and unverifiable answers become "not found in this notice". Generic prompts — any notice type, not jobs only.
- **Extraction:** generic `doc_type`/`kind` (government/private job, scheme, scholarship, admission, exam, other) with title, start + last date, age, qualification (+%), gender, vacancies, salary, official `apply_link`, and a quote+page `evidence` entry per key fact. Code validation flags impossible values (start after last date, min age above max) in `needs_review`.
- **Calculators:** all arithmetic is pure code now — `calc_age`, `calc_days_left`, `calc_age_limit` (with relaxation), `calc_fee_total`, `calc_percentage` agent tools that return their working. The model never calculates.
- **Shared notice library:** file + cleaned-text fingerprints; the same PDF uploaded by another user links to the one processed copy instantly (own tracker entry, own eligibility) instead of re-processing. Personal-looking files (marksheet/ID/filled form) are never shared. Linked users can read/ask/checklist a shared notice; deleting as a linked user removes only their link.
- **UI:** notice page shows an "Apply on the official website" button (only when an official link was extracted), doc type, start date, vacancies, salary, and a shared-notice note.
- Tests: `tests/test_phase_v2.py` (9 new); full suite green. Deferred from the V2 plan pending golden-set scores: pgvector, external reranker, notice versions/corrigenda, Q&A store, live step trace, SAM.

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
