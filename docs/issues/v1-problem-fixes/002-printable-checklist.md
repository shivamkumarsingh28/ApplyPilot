# 002 — No printable checklist for deadline day

**Folders:** `backend/` + `frontend/` · **Severity:** 🟡 Missing feature · **Status:** ✅ Added

## Problem
The design covers reading a notice and checking eligibility, but a real user
on submission day had no single page to print: key facts, eligibility verdict,
which documents are ready/missing, and what to do on the portal were spread
across three screens.

## Found in (gap)
- No checklist anywhere: `backend/app/api/routes/` had no export/print route,
  and `frontend/app/notices/[id]/page.tsx` had no print action.
- The building blocks already existed and were reused, not duplicated:
  `services/eligibility.py` (`evaluate`), `services/readiness.py`
  (`readiness`), `services/profile_store.py` (`load_profile`).

## Fix
| Folder | File | Line | Change |
|---|---|---|---|
| `backend/app/services/` | `export.py` (new) | 21 | `checklist_html(notice_title, structured, eligibility, readiness, profile)` builds a self-contained printable HTML page. Every user/notice value passes through `html.escape` (`_h()`), `@media print` hides the button, and the button calls `window.print()` (Print / Save as PDF). |
| `backend/app/api/routes/` | `export.py` (new) | 16–24 | `GET /notices/{notice_id}/checklist` — owner-checked with `get_owned` (another user's notice → 404), combines eligibility + readiness + profile. |
| `backend/app/api/` | `router.py` | 3, 6 | Registers the new `export` route module. |
| `frontend/app/notices/[id]/` | `page.tsx` | 108–112 | "Before you apply" card with a **Print checklist** button. It fetches via `api.blob()` (the endpoint needs the login token — a plain `<a href>` would 401) and opens the result in a new tab. |

## Feature affected
Notice page (wireframe 2) — the "Ready to apply?" journey now ends in a
printable artifact. Also used on paper by users with poor connectivity.

## How to verify
```powershell
cd backend
python -m pytest tests/test_export_features.py::test_checklist_is_printable_and_owner_only -q
```
Asserts: 200 + `text/html`, applicant name and missing-document sections
present, other user → 404, no token → 401. Live-server smoke test also
fetched the checklist for a real registered user and matched the applicant
name and "Still missing" list.
