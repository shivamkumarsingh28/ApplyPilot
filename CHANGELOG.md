# Changelog

## UI/UX Design Spec implementation (unreleased)

Implemented from `docs/Phase_Plan_docs/ApplyPilot_UI_UX_Design_Spec.md` (build order steps 1-10 where the backend supports it):

- **Design system (5.1-5.4):** exact spec tokens as CSS variables (primary #2f5bea, success #157f4b, warning #a15c00…), 16px body, 44px touch targets, radius/shadow per spec, dark theme retained and re-mapped. Components: StatusChip (icon+word, never colour alone), Skeleton, Spinner, Toast+Undo, ConfirmDialog (names the item), Empty states with one action, Citation/verbatim quote styling, checklist, dropzone, tabs, board.
- **App shell (3):** desktop left sidebar; phone bottom bar (Home, Assistant, Notices, Vault, More sheet); floating Help button opening a per-screen drawer fed by one content file (`lib/helpContent.ts`).
- **S1 Landing** for signed-out visitors (hero "Stop losing chances to paperwork", problem cards, 4 steps, channels, safety, FAQ). **S6 Home:** greeting, live Setup checklist (4 steps with times, computed from real profile/notices/documents/bot-status), Next-deadline hero, quick actions, applications, recent notices, connect card. **S3 Login:** provider buttons (shown when configured), Show password, live "at least 8 characters" rule.
- **S7/S8 Notices:** tabbed add (Upload file dropzone / Paste text), named ingest steps (Reading → Checking safety → Finding key facts → Ready), search, safety chips with words. **S9 Notice detail:** tabs Overview (fact cards with page chips + "Found in notice / Please check"), Eligibility (verdict chip, per-check rows, add-missing-field prompt, re-check), Ask (verbatim quotes), Documents (readiness + Fix photo + checklist), Safety.
- **S10/S8.4 Assistant:** notice selector kept, suggestion chips, "Checked answer" chip, collapsible **How I answered** trace (safety, helper chosen + why, tools used — no private values), thumbs up/down wired to `/assistant/feedback`.
- **S12 Vault:** grouped by type, copies indented under originals with APP refs, storage bar. **S13 Tracker:** Closing-soon group + List/Board views with status moves. **S14 Profile:** completeness bar for the fields eligibility needs. **S15 Chat apps (new page):** Telegram link-code flow with copy field, 10:00 countdown, auto-poll to Connected, Disconnect (`/bot/status`, `/bot/unlink` added), WhatsApp honest-Experimental card, safety line. **S16 Extension (new page), S17 Settings (new page):** language/share preferences, download-my-data, delete with confirmation dialog (server deletion not yet enabled — stated honestly).
- **Bug found & fixed while verifying (affected every real user):** Chrome Private Network Access — the website's API calls from localhost were blocked in the browser while curl worked. Fixed with native `allow_private_network` + middleware in `backend/app/main.py`, regression-tested. Also removed 4 orphan profile rows left by an earlier smoke cleanup that 500'd registration.
- Verified: frontend build clean (13 routes incl. /chat-apps, /extension, /settings), backend 133 tests, and a live phone-viewport walkthrough (landing → register → Home checklist → Help drawer), screenshot-checked.

## Tool Calling Inventory: framework + Priority 1/2 tools (unreleased)

Implemented from `docs/Phase_Plan_docs/ApplyPilot_Tool_Calling_Inventory.md` (audited first: the doc's "9 tools exist" was stale — 14 existed; built what was genuinely missing, unified aliases instead of duplicating, e.g. `notice_facts` kept over `get_notice_facts`).

- **Framework (build step 1):** tools declare `kind` (read/compute/write/destructive/external) + `confirm`; write/destructive tools return a *proposal* first and run only on `confirm=true`; `needs_input` is a normal reply rendered as one friendly question; every call is timed, write/external calls are audit-logged with tool name + ids only; `MAX_STEPS` 3->4; native tool calling added (`chat_with_tools`, parallel calls preserved) with the portable JSON protocol as fallback. Bots get everything free (they call the same assistant).
- **New tools (25):** get_key_answers, find_in_notice, get_notice_page, get_ingest_status, explain_eligibility_rule (exact quote + page), check_qualification, check_marks, what_if_eligibility (never saves), rank_notices_for_me, get_profile_summary, update_profile_field (confirmed, validated), parse_date_text, validate_contact_fields, record_feedback, set_active_notice, list_documents, get_storage_usage, list_applications, create_application, update_application_status, get_application_checklist, find_duplicate_documents, check_url_trust, find_in_library, link_library_notice, is_public_notice, convert_grade, inspect_image, detect_face, check_photo_quality (blur/brightness/face), parse_color_name, get_image_requirements, prepare_for_notice (recipe; saves a copy, original untouched), make_application_copy, list_application_documents, get_document_info. Registry: 50 tools.
- **Agents:** 7 agents now (notice, eligibility, tracker, photo, profile, documents, discover), each <=12 tools (<=8 own + 3 shared chat helpers). `notice_facts` now returns organisation/doc_type/vacancies/salary/apply_link too.
- **Fixes while here:** keyword-router collisions ("documents are missing" -> eligibility not documents; "which notice should I apply first" -> tracker). Tool-choice keyword score is unit-tested.
- **Deferred (deliberate):** notice versions/corrigenda (foundation feature), reminders/sending tools (need the bot delivery decision), PDF merge/compress tool-pack (pypdf engine work, its own phase), admin-agent tool set, MCP exposure. Each remains catalogue-listed and unblocked by this framework.
- Verified: 132 backend tests (12 new: registry shape, needs_input, two-step confirmation proving no write happens, what-if purity, foreign-user blindness, per-agent list sizes), ruff clean.

## Photo Studio, professional edition (unreleased)

- **Real-user framing:** portals reject files for pixels, KB range, format and background — and many users want ONLY a resize. The studio is now a mode-based dashboard: **Resize only** (exact pixels/KB/format, colours and background provably untouched — a "Colour untouched" check proves it, with Crop / Fit-with-padding / Stretch shape handling), **Full photo fix** (face crop + background, now with an explicit "keep my original background" switch), **Signature**, and **Document scan** (certificates/marksheets: gentle light/shadow flattening, fit-inside so no edge is ever cut, no face/background logic).
- Format conversion JPG<->PNG wired through (was silently ignored), notice rules still override, the portal-background rule still wins with a warning.
- UI: mode cards, common-size presets (Passport 35×45mm, SSC/UPSC 200×230, state portal, signature), px/cm unit toggle (@300dpi), target-KB, before/after with final KB, named vault save (`save_as`) with saved/not-saved state; originals never modified, results save as application copies.
- Tests: 7 new studio tests (exact pixels, colour-untouched, KB 20–50 exact, PNG bytes, document-mode guarantees, API modes + named save). Full suite 121 green, frontend build clean.

## CRITICAL fix: blank answers from an unauthorized Meta key + poisoned cache (unreleased)

- **Root cause (found live):** the configured `META_API_KEY` is rejected by Meta — HTTP 401 `invalid_api_key`. The provider swallowed the error shape and the app stored the resulting **empty string** in the answer cache, so the notice page replayed a blank answer forever, labelled "saved answer (no model call)", with stray page citations (2, 4, 6) from retrieval. All 7 rows in the dev DB cache were poisoned; **purged**.
- **Fixes:** (1) the provider now raises `LLMError` on HTTP errors with the provider's own message (401s never retry) and on empty success bodies; (2) empty answers are **never cached**, poisoned rows are deleted on sight, and empty/unverifiable model text falls back to extractive source words; (3) the notice page shows a plain "model returned an empty answer" message instead of a blank; (4) `/health` now live-probes the Meta API (`api_status`, model, embeddings) so a bad key is visible instead of silent.
- **Action for the owner:** replace `META_API_KEY` in `.env` with a valid key (Meta AI Studio), then check `/api/v1/health` shows `api_status: ok`. Until then the app answers extractively/offline.
- Verified: backend 114 tests (new regression tests for empty body, 401 surfacing, poisoned-cache replay), ruff clean, frontend build clean. Live `/health`: embeddings `nomic-embed-text`, llm `api_status: error` — exactly the unauthorized-key state.

## Llama embeddings, verbatim answers, notice-page Ask fix (unreleased)

- **Embeddings (confirmed choice):** Meta has no embeddings endpoint, so the default embedding model is now **local Llama-stack Ollama `nomic-embed-text`** (768-dim; one-time `ollama pull nomic-embed-text`). Hash vectors remain the automatic fallback — uploads never fail. Fixed a real bug on the way: the embeddings-only HTTP client was rejected by its own constructor (`model=""`), silently forcing hash vectors forever; also raised `emb-llama` config + `.env.example`, and enabled it in the local `.env`. Live check: fee-question↔fee-text similarity 0.754 (hash: 0.405) vs 0.485 unrelated.
- **Verbatim answers:** every Ask response now carries `verbatim` — the exact sentence(s) copied from the PDF that support the answer (ranked by the answer's own figures), plus `verified` when every date/number in the answer matches the source. The notice page shows the quote as “exact text, page N”. Unverifiable model answers still become "not found", after one exact-copy retry.
- **Notice-page Ask fix (the `/notices/{id}` bug):** the whole-notice verifier compared raw digit strings, so a model rewriting `14 November 2026` as `2026-11-14` failed verification → spurious "not found" on the detail page while other paths answered from cache/extractive. Dates/numbers are now normalised (ISO/text/numeric dates, money punctuation) before comparison — regression tests cover reformatted dates and invented ones.
- **Not-found gate for neural embeddings:** sharper embeddings retrieve *something* for every question; the offline path now also requires a keyword overlap, so off-topic questions (Mars salary) still answer "not found".
- Verified: backend 111 tests, ruff clean, frontend build clean.

## Dynamic profile fields + custom document types (unreleased)

- **Feasibility verdict:** possible and safe, because the profile is already an encrypted JSON blob — dynamism lives in a governed `extra_fields` list, not in arbitrary keys.
- Profile: users can add their own fields (text / number / date / dropdown with choices, max 30) on the Profile page. Filled custom values are offered by the form mapper on label-matching form fields, **always flagged for review** — filled, never auto-trusted. Guards: keys cannot shadow built-in fields, sensitive names (Aadhaar/passport/PAN/bank/card/PIN/OTP) are refused with a reason, numbers/dates/options are type-validated, duplicates rejected.
- Vault: choosing type "other" now allows a free-text type name ("Income Certificate"). Stored as `kind=other + custom_kind` — display and the extension's matcher (which now matches custom names to form-field labels) use it, while readiness/eligibility engine vocabulary is unchanged. Copies preserve it; sensitive names refused.
- Verified: backend 109 tests (incl. validation/safety/mapping/custom-kind), extension 14 tests, frontend build clean.

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
