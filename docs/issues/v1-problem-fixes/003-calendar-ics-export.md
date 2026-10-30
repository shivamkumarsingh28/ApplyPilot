# 003 — No calendar reminders outside the Telegram bot

**Folders:** `backend/` + `frontend/` · **Severity:** 🟡 Missing feature · **Status:** ✅ Added

## Problem
Deadline reminders existed only inside the Telegram bot
(`GET /applications/upcoming` + `bot/applypilot_bot/reminders.py`). A web-only
user — the primary audience in the design — got no reminder in the calendar
app they already use, so the "never miss a deadline" promise depended on
installing the bot.

## Found in (gap)
- `backend/app/api/routes/applications.py` — only list/create/update/delete
  and `/upcoming`; nothing exportable to a calendar.
- `frontend/app/page.tsx` (dashboard) — no calendar action.

## Fix
| Folder | File | Line | Change |
|---|---|---|---|
| `backend/app/services/` | `export.py` (new) | 64 | `ics_calendar(applications)` builds a valid iCalendar file: for each open application with a deadline, **three** `VEVENT`s — 7 days, 3 days and 1 day before — at 09:00 local (`for days_before, label in ((7, "7 days"), (3, "3 days"), (1, "1 day"))`, line 75). Summary/description text is escaped (`\ ; ,` newline). |
| `backend/app/api/routes/` | `export.py` (new) | 26–33 | `GET /applications/calendar.ics` — only the caller's `planned`/`in_progress` applications with deadlines, returned as `text/calendar` with an attachment filename. |
| `frontend/app/` | `page.tsx` | 23, 39 | Dashboard "At a glance" card gets an **Add deadlines to my calendar (.ics)** button that downloads the file via `api.blob()`. |

## Feature affected
Tracker + dashboard (wireframes 1 and 5). Reminders now work in Google
Calendar, Outlook and Apple Calendar with no bot and no account linking.

## How to verify
```powershell
cd backend
python -m pytest tests/test_export_features.py::test_calendar_has_three_reminders_per_deadline -q
```
Asserts exactly 3 events for the 14 Nov 2026 sample deadline, including
`20261107T090000` (7 days before) and `20261113T090000` (1 day before), and
0 events for a user with no applications. Same counts confirmed against the
live server.
