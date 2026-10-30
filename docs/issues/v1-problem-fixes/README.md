# v1 Problem Fixes — issue register

Every problem found while finishing ApplyPilot v1, documented **folder-wise,
file-wise, and line-wise**: where it was found, how it was resolved, which
feature it affects, and how it was verified. One file per issue — start here.

| # | Issue | Folder | Severity | File(s) | Status |
|---|---|---|---|---|---|
| 001 | Photo Studio crashes on OpenCV 5 (`CascadeClassifier` removed) | `backend/` | 🔴 Breaking — 2 failing tests, face crop broken on new installs | [001-opencv5-photo-studio-crash.md](001-opencv5-photo-studio-crash.md) | ✅ Fixed |
| 002 | No printable checklist for deadline day (wireframe gap) | `backend/` + `frontend/` | 🟡 Missing feature | [002-printable-checklist.md](002-printable-checklist.md) | ✅ Added |
| 003 | No calendar reminders outside the Telegram bot | `backend/` + `frontend/` | 🟡 Missing feature | [003-calendar-ics-export.md](003-calendar-ics-export.md) | ✅ Added |
| 004 | Dashboard "Time saved" was in the wireframe but not in the API/UI | `backend/` + `frontend/` | 🟡 Missing feature | [004-dashboard-summary-time-saved.md](004-dashboard-summary-time-saved.md) | ✅ Added |
| 005 | Saved notices could not be filtered by scam level | `backend/` | ⚪ Missing feature | [005-scam-level-filter.md](005-scam-level-filter.md) | ✅ Added |
| 006 | Test environment had no working Python/pytest (Windows) | `backend/`, `extension/` | ⚪ Setup only — no code change | [006-test-environment-setup.md](006-test-environment-setup.md) | ✅ Resolved |

## How each issue file is written

1. **Problem** — what a user or developer actually sees.
2. **Found in** — exact folder → file → line (before the fix, where that matters).
3. **Root cause** — why it happened.
4. **Fix** — exact folder → file → line after the fix, and what changed.
5. **Feature affected** — which part of the product this touches.
6. **How to verify** — the exact command/test that proves it.
7. **If it comes back** — first place to look.

## Verification totals after all v1 fixes

| Suite | Result |
|---|---|
| `backend` — `python -m pytest -q` | **84 passed** (was 78 passed / 2 failed) |
| `bot` — `python -m pytest -q` | 10 passed |
| `extension` — `npm test` | 4 passed |
| `frontend` — `npm run lint` + `npm run build` | clean |
| Live server smoke test (register → notice → summary → .ics → checklist) | passed |

Conventions for future versions: create `docs/issues/v2-problem-fixes/` with
the same one-file-per-issue format and add its register to this file.
