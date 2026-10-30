# API reference

Base address: `/api/v1`. Interactive docs with try-it buttons: `http://localhost:8000/docs`.

Send the login token in every call that needs it: `Authorization: Bearer <token>`. Get a token from `POST /auth/login`.

Errors use the shape `{"detail": "message"}`. Common codes: 401 not signed in, 403 not allowed, 404 not found (also used for other people's items), 413 file too big, 415 wrong file type, 422 bad input, 429 too many requests.

This file is generated from the running app (`/openapi.json`). Re-generate it after you add routes.

## health

| Method | Path | What it does | Who can call |
|---|---|---|---|
| GET | `/health` | Health | none |

## auth

| Method | Path | What it does | Who can call |
|---|---|---|---|
| POST | `/auth/login` | Login | none |
| GET | `/auth/me` | Me | signed-in user |
| POST | `/auth/register` | Register | none |

## profile

| Method | Path | What it does | Who can call |
|---|---|---|---|
| GET | `/profile` | Get profile | signed-in user |
| PUT | `/profile` | Put profile | signed-in user |

## documents

| Method | Path | What it does | Who can call |
|---|---|---|---|
| GET | `/documents` | List documents | signed-in user |
| POST | `/documents` | Upload | signed-in user |
| DELETE | `/documents/{doc_id}` | Remove | signed-in user |
| GET | `/documents/{doc_id}/download` | Download | signed-in user |

## notices

| Method | Path | What it does | Who can call |
|---|---|---|---|
| GET | `/notices` | List notices | signed-in user |
| POST | `/notices` | Create notice | signed-in user |
| DELETE | `/notices/{notice_id}` | Delete notice | signed-in user |
| GET | `/notices/{notice_id}` | Get notice | signed-in user |
| POST | `/notices/{notice_id}/ask` | Ask | signed-in user |
| GET | `/notices/{notice_id}/eligibility` | Eligibility | signed-in user |
| GET | `/notices/{notice_id}/readiness` | Notice readiness | signed-in user |
| GET | `/notices/{notice_id}/checklist` | Printable HTML checklist | signed-in user |
| GET | `/notices?scam_level=low\|medium\|high` | List notices filtered by scam level | signed-in user |

## photo

| Method | Path | What it does | Who can call |
|---|---|---|---|
| POST | `/photo/process` | Process | signed-in user |

## forms

| Method | Path | What it does | Who can call |
|---|---|---|---|
| POST | `/forms/map` | Map form | signed-in user |

## applications

| Method | Path | What it does | Who can call |
|---|---|---|---|
| GET | `/applications` | List applications | signed-in user |
| POST | `/applications` | Create | signed-in user |
| GET | `/applications/summary` | Dashboard counts, next deadline, time saved | signed-in user |
| GET | `/applications/upcoming` | Upcoming | signed-in user |
| GET | `/applications/calendar.ics` | Calendar file with 7/3/1-day reminders | signed-in user |
| DELETE | `/applications/{app_id}` | Delete | signed-in user |
| PATCH | `/applications/{app_id}` | Update | signed-in user |

## assistant

| Method | Path | What it does | Who can call |
|---|---|---|---|
| POST | `/assistant/chat` | Chat | signed-in user |

## bot

| Method | Path | What it does | Who can call |
|---|---|---|---|
| POST | `/bot/link` | Link | bot secret header |
| POST | `/bot/link-code` | Create link code | signed-in user |

## admin

| Method | Path | What it does | Who can call |
|---|---|---|---|
| GET | `/admin/audit` | Audit log | admin |
| GET | `/admin/stats` | Stats | admin |
| GET | `/admin/users` | List users | admin |
| PATCH | `/admin/users/{user_id}` | Update user | admin |
