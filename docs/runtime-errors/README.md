# Runtime errors — why they happen and how to fix them

A separate guide for the error class behind:

```
ImportError: cannot import name 'ArgsKwargs' from 'pydantic_core._pydantic_core' (unknown location)
```

For setup from scratch see [../GETTING_STARTED.md](../GETTING_STARTED.md).
For day-to-day running see [../RUNBOOK.md](../RUNBOOK.md).

---

## 1. The `ArgsKwargs` error that hit this project (fixed)

### What the terminal showed

```
Process SpawnProcess-1:
  File "...\backend\app\main.py", line 5, in <module>
    from fastapi import FastAPI, Request
  ...
  File "...\pydantic\version.py", line 7, in <module>
    from pydantic_core import __version__ as __pydantic_core_version__
ImportError: cannot import name 'ArgsKwargs' from 'pydantic_core._pydantic_core' (unknown location)
```

### Why it happened

1. `pydantic` is split in two: pure-Python `pydantic` + a compiled Rust
   extension `pydantic_core._pydantic_core` (a `.pyd` file on Windows).
2. A `.pyd` only loads in the exact CPython it was built for. Its filename
   says which: `_pydantic_core.cp312-win_amd64.pyd` = CPython 3.12.
3. The venv in `backend/.venv` was running **Python 3.14.2** but contained
   the **cp312** file. Python 3.14 could not load it, so every name inside
   it (`ArgsKwargs`, …) was missing → `(unknown location)`.
4. Everything that imports pydantic died: FastAPI → uvicorn → your app.
   Your own code (`app/main.py`) was never the bug.

Diagnosis that proved it (30 seconds):

```powershell
backend\.venv\Scripts\python.exe --version          # 3.14.2
Get-ChildItem backend\.venv\Lib\site-packages\pydantic_core\*.pyd
# _pydantic_core.cp312-win_amd64.pyd   <-- cp312 != 3.14  => wrong venv
```

### The fix that worked

Never copy or reuse a `.venv` across Python versions. Rebuild it with the
interpreter you actually run:

```powershell
cd backend
Rename-Item .venv .venv-broken-cp312
C:\Users\<you>\AppData\Local\Python\pythoncore-3.14-64\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check                 # No broken requirements found.
.\.venv\Scripts\python.exe -c "from app.main import app; print(app.title)"
.\.venv\Scripts\python.exe -m pytest -q                 # 84 passed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
curl.exe http://127.0.0.1:8000/api/v1/health            # {"status":"ok",...}
```

A narrow fix (`pip install --force-reinstall pydantic-core`) also repairs a
single bad package. Rebuilding is safer when you don't know how many
packages are mismatched — here `cryptography`/`cffi` were broken too.

Prevention now in place:

- `backend/requirements.txt` pins `pydantic` and `pydantic-core` as a pair
  with a comment explaining this failure.
- `backend/requirements-lock.txt` is a `pip freeze` of the verified set.
  Reproduce it exactly with `pip install -r requirements-lock.txt`.
- Rule: **one venv per Python version**. Upgrading Python = new venv.

> Note: `.venv-broken-cp312` may refuse to delete while an old terminal
> still runs its uvicorn. Close that terminal, then delete the folder.

---

## 2. Build error vs runtime error

| Kind | When you see it | Example in this project |
|---|---|---|
| Syntax / build | Before anything runs | `tsc --noEmit` fails; Python `SyntaxError` |
| Import / startup | Process starts, then dies | `ArgsKwargs` above; `ModuleNotFoundError: app` when you run uvicorn from the wrong folder |
| Runtime | App is up, a request or line triggers it | `ZeroDivisionError`, `RuntimeError: ENCRYPTION_KEY must be set in production` in `app/core/crypto.py`, a 500 on one endpoint |

Same code can pass the build and still fail at runtime, because runtime
depends on data, environment variables, files, and installed binaries.

---

## 3. The technique: a loop that works for any runtime error

1. **Reproduce small.** Shrink the failing command until it still fails:
   `python -c "from pydantic import BaseModel"` instead of full uvicorn.
   If the small one passes, add pieces back one at a time (binary search).
2. **Read the traceback bottom-up.** The last line is the error; the frames
   above are the path. Ask: is the failing frame *my code* or a library?
   `(unknown location)` / a `.pyd` = binary/environment problem, not logic.
3. **Check the environment before the code.** `python --version`,
   `pip list`, `pip check`, which venv is active, does `.env` exist,
   is the port already in use? Most "mystery" runtime errors live here.
4. **Form one hypothesis, test it.** "cp312 file in a 3.14 venv" → list the
   `.pyd` files. One experiment at a time; write down what you tried.
5. **Fix the root cause, surgically.** Reinstall/rebuild, fix the one line,
   add the missing env var. Don't refactor neighbours while debugging.
6. **Verify at three levels.** Import (`from app.main import app`),
   tests (`pytest -q`), live server (`/api/v1/health`). All three were run
   for the fix above.
7. **Make it stay fixed.** Pin versions, add a test, or improve the error
   message so the next person skips steps 1–4.

Useful tools: VS Code debugger (breakpoint on the raising line, inspect
locals), `python -m pdb script.py`, logging the inputs before the crash,
and `try/except` that logs then re-raises during development.

---

## 4. Create a runtime error on purpose (safe practise)

Nobody learns debugging from code that works. Break things deliberately,
in files that cannot hurt real data:

```powershell
cd backend
.\.venv\Scripts\python.exe ..\docs\runtime-errors\examples\make_runtime_error.py all
.\.venv\Scripts\python.exe ..\docs\runtime-errors\examples\make_runtime_error.py 4
```

What each demo teaches:

| # | Error | Lesson |
|---|---|---|
| 1 | `ImportError` | Mismatched wheel/venv — check the `.pyd` suffix vs `python --version` |
| 2 | Unhandled `RuntimeError` | Uncaught exceptions kill the request/process; FastAPI turns them into 500s |
| 3 | Handled `IndexError` | Catch specific errors, log, return something sane |
| 4 | `ZeroDivisionError` | Compiles fine, only data at runtime triggers it — validate input |

Backend variant: copy demo 2's `raise` into a throwaway FastAPI route,
watch uvicorn log the traceback and return 500, then register an
`exception_handler` like the ones in `app/main.py` and see a clean JSON
error instead. Delete the route afterwards.

Frontend variant: `throw new Error("practice")` inside a component, watch
the dev overlay, then wrap it in an error boundary. Revert afterwards.

---

## 5. Handling patterns used in this codebase

- **Fail fast on bad config:** `app/core/crypto.py` raises
  `RuntimeError("ENCRYPTION_KEY must be set in production")` at startup
  instead of encrypting with a weak key later.
- **Turn known errors into clean HTTP responses:** `app/main.py` registers
  handlers so `UnreadableDocument` → 422 and `LLMError` → 502 with a safe
  message, not a traceback leaked to the browser.
- **Validate at the boundary:** pydantic models reject bad input before
  your logic runs, converting runtime surprises into 422s.
- **Tests as reproduction:** a failing case becomes a pytest; `pytest -q`
  (84 tests) is the regression net run after every environment fix.

## 6. Checklist when the terminal goes red

- [ ] Which Python/Node, and which venv? (`python --version`, prompt prefix)
- [ ] `pip check` clean? `.pyd` suffixes match that Python?
- [ ] Running from the right folder? (`uvicorn app.main:app` needs `backend/`)
- [ ] `.env` present, `ENCRYPTION_KEY` set for production?
- [ ] Smallest reproduction still failing?
- [ ] After the fix: import ✓, tests ✓, `/api/v1/health` ✓?
