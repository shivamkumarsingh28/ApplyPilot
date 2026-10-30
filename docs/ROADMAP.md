# Roadmap

Work is split into phases so each one is small enough to finish and test.

## Phase 1: core product (done)

- [x] Backend API: accounts, profile, document vault, notices, photo studio, form mapper, tracker
- [x] Notice reading: rules + model extraction, safety check, question answering with page numbers
- [x] Rules-based eligibility engine
- [x] Website: sign in, dashboard, notices, photo studio, vault, tracker, profile
- [x] Chrome extension: scan, review, fill

## Phase 2: models, security, agents, chat (done in this session)

- [x] Model switch: `mock`, `llama_local` (Ollama), `meta` (Muse), `openai_compat`
- [x] Roles (user, admin), account disable, audit log
- [x] Guardrails (input, document, output), rate limits, upload checks, security headers
- [x] Supervisor, four agents, nine tools, per-user isolation
- [x] Telegram bot with reminders; WhatsApp adapter (experimental)
- [x] Docker Compose (database, API, website, bot, optional Ollama), CI, docs

## Phase 3: next session

- [ ] **Your decision on MCP** (see [MCP_PLAN.md](MCP_PLAN.md)) and build it
- [x] Documentation that walks through every file ([CODE_GUIDE.md](CODE_GUIDE.md)) plus a runbook ([RUNBOOK.md](RUNBOOK.md)) and feature map ([FEATURES_AND_ROADMAP.md](FEATURES_AND_ROADMAP.md))
- [x] Full-use-case additions: printable checklist, calendar (.ics) reminders, dashboard summary with time saved, scam-level filter; fixed Photo Studio on OpenCV 5
- [ ] Run against the real services and fix what breaks: Meta Model API, Ollama, Telegram, Docker, PostgreSQL
- [ ] Website pages for the assistant chat (exists) and the admin area
- [ ] Alembic migrations, Redis rate limiting, object-storage adapter

## Phase 4: quality and growth

- [ ] Test extraction on 30+ real notices and publish accuracy numbers
- [ ] Test photo studio on real photos (face detection, background removal), try SAM 3.1
- [ ] Better extension: iframes, custom dropdowns, "explain this field"
- [ ] Hindi and other languages for answers
- [ ] Community-checked form specs shared between users (needs moderation)
- [ ] WhatsApp reminders with approved templates

## Known gaps (be honest with users)

- Regex rules were written against one fictional sample and a few wording variants. Real notices are messier. The model layer and the "check this" flags exist because of that.
- The upper-age rule differs between notices ("up to 21" can mean before or after the 21st birthday). We show the exact age so the user can decide.
- Face detection uses OpenCV's classic detector. It can miss faces in poor light.
