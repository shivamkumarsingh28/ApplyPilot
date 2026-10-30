# Architecture

## The big picture

```
 Website (Next.js)   Chrome extension   Telegram / WhatsApp bot
        \                  |                  /
         \                 |                 /
          +-------->  API  (FastAPI)  <-----+
                           |
     +----------+----------+-----------+------------+
     |          |          |           |            |
  Accounts   Notices    Photo       Form        Assistant
  + roles    + search   studio      mapper      (supervisor
  + audit    + checks                           + agents + tools)
     |          |          |           |            |
     +----------+----------+-----------+------------+
                           |
          Database (SQLite / PostgreSQL) + encrypted file storage
                           |
              AI model provider (mock | llama_local | meta | openai_compat)
```

All clients talk to the same API with the same login token. The API is the only part that touches data, so the security rules live in one place.

## Folder map (backend)

```
backend/app/
├── main.py              Starts the app, adds CORS and security headers.
├── core/                Settings, passwords, tokens, encryption, rate limits, upload checks.
├── db/                  Database connection and table definitions (models.py).
├── schemas/             Shapes of requests and responses (Pydantic).
├── api/
│   ├── deps.py          "Who is calling?" and "may they do this?" checks.
│   └── routes/          One file per feature: auth, profile, documents, notices, photo,
│                        forms, applications, assistant, bot, admin, health.
└── services/            The real work. Routes stay thin and call these.
    ├── llm/             Model providers behind one interface.
    ├── agents/          Supervisor, agents, tools.
    ├── extraction.py    Notice text -> structured facts.
    ├── eligibility.py   Rules engine (no AI).
    ├── rag.py           Search + answer from a notice.
    ├── scam_check.py    Fake-notice warning signs.
    ├── photo_studio.py  Photo and signature fixing.
    ├── form_mapper.py   Form fields -> profile values.
    ├── guardrails.py    Input and output safety checks.
    └── ...
```

Rule of thumb: **routes handle HTTP, services handle logic.** If you add a feature, write the logic in `services/` with tests, then add a small route.

## What happens when you add a notice

1. `routes/notices.py` receives the file or text. It checks the real file type (not just the name).
2. `services/pdf_text.py` gets the text. Digital PDFs are read directly. Scanned files go to a vision model.
3. `services/extraction.py` finds dates, ages, fee, documents, photo rules. First by rules (exact patterns), then the model fills gaps. If they disagree, the user sees a "check this" flag.
4. `services/scam_check.py` looks for warning signs. `guardrails.looks_like_injection` flags text that tries to command an AI.
5. `services/rag.py` cuts the text into chunks and stores a search vector for each.
6. An item is added to the tracker with the deadline.

## What happens when you ask a question

**On a notice page** (`/notices/{id}/ask`): guardrail check, then search the chunks, then answer using only those chunks. If nothing relevant is found, we say so. We never guess a date or fee.

**In the assistant** (`/assistant/chat`, also used by the bot): see [AGENTS.md](AGENTS.md).

## Why eligibility is not done by the AI

Age and marks are arithmetic. A model can get arithmetic wrong, and a wrong "you are eligible" costs someone a year. So the model only **reads** the rules from the notice. A plain Python function (`services/eligibility.py`) applies them, and every check is shown with its reason.

## Offline mode

With `LLM_PROVIDER=mock`, each service has a rule-based path. This keeps tests fast and free, and shows that the model improves the product but is not needed for it to work.

## Data model (main tables)

| Table | Holds |
|---|---|
| users | email, password hash, role, active flag |
| profiles | the profile as one **encrypted** blob |
| documents | file info. The file itself is encrypted on disk. |
| notices, notice_chunks | notice text, extracted facts, search vectors |
| applications | tracker rows and deadlines |
| bot_links | one-time codes that link a chat to an account |
| audit_logs | who did what (no contents) |
