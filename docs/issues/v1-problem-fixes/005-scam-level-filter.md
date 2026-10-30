# 005 — Saved notices could not be filtered by scam level

**Folder:** `backend/` · **Severity:** ⚪ Missing feature · **Status:** ✅ Added

## Problem
Every notice gets a scam report (`low` / `medium` / `high`), and the notices
list already displays the level — but a user with many saved notices (the
normal case after a few weeks) could not ask "show me only the risky ones"
to triage. The "Fake? OK" check in wireframe 2 did not scale to a list.

## Found in (gap)
- File: `backend/app/api/routes/notices.py`
- Function: `list_notices()` — returned all of the caller's notices with no
  filtering; `scam_level` was only an output field (`NoticeListItem`).

## Fix
| Folder | File | Line | Change |
|---|---|---|---|
| `backend/app/api/routes/` | `notices.py` | 76 | `list_notices(scam_level: str | None = None, ...)` — new optional query parameter. |
| `backend/app/api/routes/` | `notices.py` | 78–79 | When given, keep only notices whose stored `scam_report.level` equals it. Filtering is done on the already owner-scoped rows, so a user can never filter into someone else's notices. |

Endpoint: `GET /notices?scam_level=low|medium|high` (documented in
`docs/API.md`).

## Feature affected
Notice safety triage (wireframe 2's "Fake?" check, at list scale). The
frontend can add a level dropdown on the notices page later using the same
parameter; no further backend change is needed.

## How to verify
```powershell
cd backend
python -m pytest tests/test_export_features.py::test_scam_level_filter -q
```
Asserts: `?scam_level=low` returns the sample notice (level `low`),
`?scam_level=high` returns an empty list for the same user.
