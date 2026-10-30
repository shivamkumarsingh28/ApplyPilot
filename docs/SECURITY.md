# Security

This page lists every protection in the project, where it lives, and what is **still your job** before you go live.

## 1. Who can do what (roles)

| Role | Can do |
|---|---|
| `user` | Everything with **their own** data |
| `admin` | List accounts, enable or disable accounts, change roles, read the audit log, see totals |

- Admins are created by putting an email in `ADMIN_EMAILS` before that person registers.
- The role is read from the database on **every request**, not from the login token. If you disable an account or remove a role, it works immediately.
- Admins **cannot read** other users' notices, profile or files. Those routes only accept the owner. This is on purpose: a stolen admin account cannot leak user data.
- An admin cannot change their own role or status (stops accidental lock-out).

Code: `api/deps.py` (`get_current_user`, `require_role`, `get_owned`), `api/routes/admin.py`.

## 2. "You only see your own data"

Three layers:

1. **Every query is filtered by the owner.** `get_owned()` returns the same "not found" error for a missing id and for someone else's id, so nobody can learn which ids exist.
2. **Agent tools have no "user" argument.** A tool gets the signed-in user from the server, not from the AI. Even if an attacker convinces the model to ask for "user 5's notices", the tool cannot do it. Unknown arguments are dropped.
3. **Tests prove it.** `tests/test_agents.py::test_user_cannot_reach_another_users_notice` and `tests/test_security.py` try to cross the line.

## 3. Login and tokens

- Passwords are hashed with bcrypt. Minimum 8 characters.
- Login tokens (JWT) expire (default 7 days). Change with `ACCESS_TOKEN_MINUTES`.
- Login and register are limited to a few tries per minute per IP. Failed logins are written to the audit log.
- The Telegram link uses a one-time code that expires in 10 minutes. The bot's token lasts 30 days.

## 4. Guardrails for the AI assistant

All in `services/guardrails.py`. They are plain code, so they cannot be argued with.

| Check | When | What it stops |
|---|---|---|
| Length and empty | Input | Huge or empty messages |
| Prompt injection patterns | Input | "Ignore previous instructions", "reveal your system prompt", "you are now..." |
| Data-access patterns | Input | "List all users", "show other users' documents", "admin password", SQL |
| Unsafe requests | Input | Fake certificates, bypassing captcha, hacking, weapons |
| Self-harm | Input | Replaces the answer with a kind message to reach a trusted person |
| Off-topic | Input (assistant only) | Poems, homework, anything not about notices, documents, eligibility, deadlines |
| Document injection | On upload | A notice that tries to command an AI gets a warning |
| Secret removal | Output | Tokens, API keys, long hashes are removed from answers |

Also: the prompts tell the model that notice text and tool results are **data, never orders**.

Guardrails are a safety net. They will not catch every clever attack. The real protection is layers 1 to 3 in section 2.

## 5. Protecting stored data

- Uploaded files are encrypted (Fernet) before they touch the disk. Profiles are encrypted in the database.
- `ENCRYPTION_KEY` is required in production. **If you lose it, the data cannot be read.** Back it up somewhere safe, separately from the database backup.
- We do **not** collect ID numbers (Aadhaar, passport, etc.) or payment numbers. The profile rejects unknown fields, and the extension never fills such fields.
- The audit log stores actions and ids only, never contents.

## 6. Upload safety

- Files are checked by their **real bytes**, not by the name or the type the browser claims (`core/uploads.py`).
- Size limits: documents 10 MB, notices 15 MB, photos 12 MB.
- Images are decoded with Pillow inside a try/except; bad files return a clear error.

## 7. Network and browser

- CORS allows only your website and the extension.
- Responses carry `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` and `Cache-Control: no-store`.
- The extension gets the page only when you click it (`activeTab`), it never submits a form, and it skips password, captcha, OTP, file and ID fields.
- The WhatsApp webhook checks Meta's HMAC signature on every call.

## 8. Limits

`RATE_LIMIT_PER_MINUTE`, `AI_RATE_LIMIT_PER_MINUTE`, `LOGIN_RATE_LIMIT_PER_MINUTE`. These stop password guessing and protect your model quota. The counters are in memory; with more than one server, move them to Redis.

## What is still your job (production checklist)

- [ ] Set `APP_ENV=production`, a long `SECRET_KEY`, and your own `ENCRYPTION_KEY`
- [ ] Serve everything over HTTPS (use a reverse proxy such as Caddy or Nginx)
- [ ] Set `CORS_ORIGINS` to your real website address only
- [ ] Use PostgreSQL with backups; test restoring a backup
- [ ] Replace local file storage with object storage (S3 or OCI) with encryption and private access
- [ ] Move rate-limit counters to Redis if you run more than one server
- [ ] Use database migrations (Alembic) instead of `create_all`
- [ ] Add malware scanning for uploads if you accept files from the public
- [ ] Review privacy law for your users (for example India's DPDP Act, GDPR) and write a privacy policy
- [ ] Add account deletion and data export if your law requires it
- [ ] Keep dependencies updated (`pip list --outdated`, `npm audit`)

## Reporting a vulnerability

Please do not open a public issue. Email the maintainers (add your address in `SECURITY.md` at the repo root).
