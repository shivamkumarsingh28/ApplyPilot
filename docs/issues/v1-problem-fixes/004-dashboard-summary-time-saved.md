# 004 — Dashboard "Time saved" was in the wireframe but nowhere else

**Folders:** `backend/` + `frontend/` · **Severity:** 🟡 Missing feature · **Status:** ✅ Added

## Problem
Wireframe 1 shows `Time saved: 6h 20m` in the dashboard header and lists
applications with readiness. The built dashboard fetched `/applications` and
`/notices` separately and showed no totals, no next-deadline summary, and no
time-saved number — the first screen a returning user sees did not answer
"where do I stand?"

## Found in (gap)
- `backend/app/api/routes/applications.py` — no aggregate endpoint; the
  frontend would have needed three calls and its own counting rules.
- `frontend/app/page.tsx` — only rendered the raw application list.

## Fix
| Folder | File | Line | Change |
|---|---|---|---|
| `backend/app/api/routes/` | `applications.py` | 27–51 | New `GET /applications/summary`: counts by status (`total`, `open`, `submitted`, `closed`), `notices` count, `documents_ready` (vault count), next open deadline (`next_deadline`, `next_title`, `next_days_left`), and `time_saved_minutes` (line 50). The heuristic is documented in the docstring, not hidden: **notice read = 20 min, tracked application = 15 min, saved document = 10 min**. |
| `frontend/lib/` | `types.ts` | 30 | `Summary` type mirroring the API response. |
| `frontend/app/` | `page.tsx` | 14, 21, 32, 38–44 | `fmtSaved()` renders minutes as `6h 20m`; the dashboard fetches `/applications/summary` and shows an "At a glance" card: open/submitted counts, notices read, documents ready, time saved, and the next deadline. |

## Feature affected
Dashboard (wireframe 1) — the home screen now matches the wireframe,
including the time-saved figure, with the calendar download (issue 003)
attached to the same card.

## How to verify
```powershell
cd backend
python -m pytest tests/test_export_features.py::test_summary_combines_counts_and_time_saved -q
```
Asserts: one notice + one tracker row → `total=1, open=1`,
`next_deadline="2026-11-14"`, `time_saved_minutes = 20 + 15 = 35`; after
marking the application submitted, `submitted=1, open=0`.
