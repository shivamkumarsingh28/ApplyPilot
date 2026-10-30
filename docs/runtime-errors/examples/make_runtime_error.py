"""Intentionally create runtime errors so you can practise fixing them.

Run from backend/ with the venv active:
    python ..\\docs\\runtime-errors\\examples\\make_runtime_error.py all

Each demo raises the same *kind* of error you meet in real life, then shows
how it looks when you handle it. Nothing here touches the database or .env.
"""

import sys
import traceback


def demo_1_import_error() -> None:
    """Same family as: ImportError: cannot import name 'ArgsKwargs' from
    'pydantic_core._pydantic_core' (unknown location).

    That real one meant the compiled .pyd was built for another CPython
    (cp312 file inside a Python 3.14 venv). Here we fake the shape safely.
    """
    print("\n--- 1. ImportError (wrong build / wrong venv) ---")
    try:
        from pydantic_core._pydantic_core import ThisNameDoesNotExist  # noqa: F401
    except ImportError:
        traceback.print_exc(limit=2)
        print("FIX: pip install --force-reinstall --no-cache-dir pydantic pydantic-core")
        print("     and check the .pyd suffix matches `python --version` (cp314 vs cp312).")


def demo_2_unhandled_runtime_error() -> None:
    print("\n--- 2. Unhandled RuntimeError (crashes the process) ---")
    try:
        raise RuntimeError("ENCRYPTION_KEY must be set in production")
    except RuntimeError:
        traceback.print_exc(limit=2)
        print("In FastAPI, register an exception_handler (see app/main.py) or this becomes a 500.")


def demo_3_handled_runtime_error() -> None:
    print("\n--- 3. Handled error (log it, return a clean message) ---")
    try:
        items: list[int] = []
        items[0]  # IndexError at runtime, code compiled fine
    except IndexError as exc:
        print(f"caught {type(exc).__name__}: {exc} -> returning empty result to the caller")


def demo_4_zero_division() -> None:
    print("\n--- 4. ZeroDivisionError (only appears when the code *runs*) ---")
    total, count = 10, 0
    try:
        print(total / count)
    except ZeroDivisionError:
        traceback.print_exc(limit=2)
        print("FIX: guard `if count == 0` before dividing, or validate input with pydantic.")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    demos = {
        "1": demo_1_import_error,
        "2": demo_2_unhandled_runtime_error,
        "3": demo_3_handled_runtime_error,
        "4": demo_4_zero_division,
    }
    for key, fn in demos.items():
        if which in ("all", key):
            fn()
    print("\nDone. Try: break one demo on purpose, read the traceback bottom-up, fix, re-run.")
