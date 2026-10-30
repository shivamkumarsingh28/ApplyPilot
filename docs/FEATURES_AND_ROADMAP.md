# Features and roadmap — the full real-world use case

ApplyPilot follows the system design (Web portal / Chrome extension / Chat bots →
API gateway → Vault, Notice AI, Photo Studio, Form Mapper → Data stores + Meta
Model API) and the 5 wireframes (dashboard, notice page, photo studio, extension
popup, Telegram bot). This document maps every screen to the code, lists the
features added to complete the user journey, and names what to build next.

## 1. The user journey, end to end

1. **Discover** — a friend forwards a notice PDF on WhatsApp/Telegram. The user
   uploads it (web or bot) instead of reading 30 pages.
2. **Understand** — key facts, scam check, eligibility with reasons, readiness %.
3. **Prepare** — fix photo/signature to the exact spec, upload missing documents
   to the encrypted vault, print the checklist.
4. **Apply** — the extension fills the live form from the profile; the user
   reviews every field and submits themselves. Nothing is auto-submitted.
5. **Track** — tracker + Telegram reminders + calendar (.ics) reminders so the
   deadline is never missed; status moves planned → in_progress → submitted.

## 2. Wireframe → implementation map

| Wireframe | Frontend | Backend |
|---|---|---|
| 1. Dashboard (applications, readiness, missing docs, time saved) | `frontend/app/page.tsx` | `GET /applications`, `GET /applications/summary`, `GET /notices/{id}/readiness` |
| 2. Notice page (key facts, eligibility, Ask this notice, Fake? OK) | `frontend/app/notices/[id]/page.tsx` | `GET /notices/{id}`, `/eligibility`, `/readiness`, `POST /notices/{id}/ask`, `GET /notices/{id}/checklist` |
| 3. Photo & signature studio | `frontend/app/photo/page.tsx` | `POST /photo/process` |
| 4. Extension popup (matched fields, Fill all, Explain) | `extension/popup.html`, `popup.js` | `POST /forms/map` |
| 5. Telegram bot (photo fix, last-date Q&A, reminders) | `bot/applypilot_bot/` | `/bot/link`, `/assistant/chat`, `/applications/upcoming` |

## 3. Features added in this pass (implemented + tested)

| # | Feature | Why a real user needs it | Where |
|---|---|---|---|
| 1 | **Printable checklist** (`GET /notices/{id}/checklist`) | On deadline day users print one page: facts, eligibility, ready/missing docs, submission-day steps | `backend/app/services/export.py`, button on notice page |
| 2 | **Calendar export** (`GET /applications/calendar.ics`) | Reminders in the calendar they already use; creates 7-day, 3-day and 1-day 09:00 reminders per open application | `backend/app/services/export.py`, dashboard button |
| 3 | **Dashboard summary** (`GET /applications/summary`) | The wireframe shows "Time saved: 6h 20m" — now real: open/submitted counts, next deadline, notices, documents, time-saved (documented heuristic: notice 20 min, tracked application 15 min, saved document 10 min) | `backend/app/api/routes/applications.py`, dashboard "At a glance" card |
| 4 | **Scam-level filter** (`GET /notices?scam_level=low\|medium\|high`) | Triage many saved notices, surface risky ones first | `backend/app/api/routes/notices.py` |
| 5 | **OpenCV 5 crash fixed** | `cv2.CascadeClassifier` was removed in OpenCV 5, which broke Photo Studio entirely on new installs. `_detect_face` now uses Haar on OpenCV <5 and YuNet on 5+, and `requirements.txt` pins `<5.0` | `backend/app/services/photo_studio.py`, `backend/requirements.txt` |

Tests: `backend/tests/test_export_features.py` (4 tests) — backend suite is
84 passed (was 80, plus the 2 previously failing photo tests now pass).

## 4. Already implemented before this pass (verified by tests)

Accounts + roles + audit log, encrypted profile and vault, notice extraction
(rules + model, `needs_review` flags), deterministic eligibility, RAG Q&A with
page citations, scam check, photo/signature studio with SAM segmenter interface,
form mapper with never-fill rules, supervisor + 4 agents + 9 tools, guardrails,
rate limits, Telegram bot with reminders, WhatsApp adapter, Docker Compose, CI.

## 5. Next features to add (prioritised)

### P1 — do next
1. **Explain-this-field in the extension** (wireframe 4 shows the button):
   hover a field → `POST /forms/explain` returns one plain-language sentence
   about what the field means and what a valid answer looks like.
2. **Deadline push reminders in the web app** (today: bot + .ics only): a daily
   job emailing/pushing 7/3/1-day warnings using the same rule as the .ics file.
3. **Document expiry warnings**: store an optional `expires_at` on documents;
   readiness drops expired documents from "have" and names them.
4. **Application fee tracker**: after submission, record fee paid + receipt
   number on the application row; summary shows total fees paid.

### P2 — growth
5. **Notice comparison**: two notices side by side (dates, fee, age, stages) —
   users apply to 3–5 similar posts at once.
6. **Family profiles**: one account, several applicants (siblings/children),
   profile switcher feeding eligibility, form mapper and vault folders.
7. **Hindi + regional language UI and answers** (model already multilingual;
   needs UI strings and answer-language prompt).
8. **Community form specs**: share anonymised field mappings for a portal so the
   next user's autofill is instant (needs moderation — see `docs/ROADMAP.md`).
9. **WhatsApp reminders with approved templates** (adapter exists; templates
   need Meta approval).

### P3 — platform
10. **MCP server** for the assistant tools (see `docs/MCP_PLAN.md`).
11. **Admin pages** in the web app (API exists: `/admin/*`).
12. **Alembic migrations, Redis rate limiting, object storage** for deployment
    at scale (see `docs/DEPLOYMENT.md`).

## 6. Which Meta model for what (from `docs/MODELS.md`)

| Job | Setting |
|---|---|
| Development, offline, tests | `LLM_PROVIDER=mock` (default) — everything above works with no model |
| Free local development | `llama_local` via Ollama (`llama3.2`, `llama3.2-vision` for scanned notices) |
| Production quality + vision | `meta` — Muse Spark via Meta Model API |
| Photo background removal | `SEGMENTER=opencv` built in; SAM 3.1 via `SEGMENTER=meta_sam` + `SAM_ENDPOINT` |
