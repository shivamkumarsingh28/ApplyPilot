# 006 — Test environment had no working Python/pytest (Windows)

**Folders:** `backend/`, `extension/` · **Severity:** ⚪ Setup only · **Status:** ✅ Resolved (no product code changed)

## Problem
On this Windows machine none of the test suites could even start:

```
python -m pytest  →  Python was not found; run without arguments to install from the Microsoft Store
py -3 -m pytest   →  No module named pytest
extension npm test → Error: Cannot find module 'jsdom'
```

Without tests, no other v1 fix could be verified.

## Found in
- Machine, not the codebase: `python` resolves to the Microsoft Store alias;
  the only interpreter is Python 3.14 via the `py` launcher, with no project
  environment. `extension/node_modules` was not installed.

## Resolution (environment only)
| Step | Command | Why |
|---|---|---|
| 1 | `cd backend && uv venv .venv --python 3.12` | Project targets Python 3.11/3.12 (`requires-python = ">=3.11"`); 3.12 avoids 3.14 wheel surprises |
| 2 | `uv pip install --python .venv\Scripts\python.exe -r requirements-dev.txt` | `uv venv` creates an environment without pip, so plain `pip install` fails with "No module named pip" — install through `uv pip --python` instead |
| 3 | `uv pip install --python .venv\Scripts\python.exe "opencv-python-headless>=4.9,<5.0"` | Match the new pin from issue 001 (the first install had pulled OpenCV 5.0.0) |
| 4 | `cd extension && npm install` | Installs the `jsdom` devDependency the scanner tests require |
| 5 | `cd frontend && npm install` | Required before `npm run lint` / `npm run build` |

## Feature affected
None directly — this unblocks verification for every other issue in this
folder. The permanent, user-facing version of these steps lives in
`docs/RUNBOOK.md` (Option A), including the Windows notes
("use `py` or `.venv\Scripts\python.exe`", OpenCV pin).

## How to verify
```powershell
cd backend ; .\.venv\Scripts\python.exe -m pytest -q    # 84 passed
cd ..\bot  ; ..\backend\.venv\Scripts\python.exe -m pytest -q   # 10 passed
cd ..\extension ; npm test                              # 4 passed
cd ..\frontend ; npm run lint ; npm run build           # clean
```
