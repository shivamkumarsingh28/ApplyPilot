"""Deadline reminders at 7, 3 and 1 days before a deadline, plus an overdue nudge.

The backend decides which applications are due (milestones + overdue); this
module only formats messages and dedupes to one reminder per application per day.
"""

from __future__ import annotations

from collections.abc import Callable

from applypilot_bot.api_client import Backend, BackendError
from applypilot_bot.store import Store

MILESTONES = "7,3,1"


def _message(row: dict) -> str:
    title, deadline, left = row["title"][:60], row["deadline"], row["days_left"]
    if left is not None and left < 0:
        return f"Overdue: {title} closed on {deadline} and is still open in your tracker. Submit now or mark it closed."
    if left == 0:
        return f"Today: {title} closes today ({deadline}). Submit now if you have not already."
    if left == 1:
        return f"Tomorrow: {title} closes on {deadline} (1 day left)."
    return f"Reminder: {title} closes on {deadline} ({left} days left)."


def due_reminders(backend: Backend, store: Store, days: int = 7) -> list[tuple[str, str]]:
    """Returns (chat_id, message) pairs that have not been sent today.

    `days` is accepted for backwards compatibility; milestone mode is used so
    users are reminded at exactly 7, 3 and 1 days, not in a rolling window.
    """
    out: list[tuple[str, str]] = []
    for chat_id, token in store.all_chats():
        try:
            rows = backend.deadlines(token, milestones=MILESTONES)
        except (BackendError, TypeError):
            try:
                rows = backend.deadlines(token, days)
            except BackendError:
                continue
        for row in rows:
            if store.reminded_today(chat_id, row["id"]):
                continue
            out.append((chat_id, _message(row)))
            store.mark_reminded(chat_id, row["id"])
    return out


def run_once(backend: Backend, store: Store, days: int, send_text: Callable[[str, str], None]) -> int:
    pairs = due_reminders(backend, store, days)
    for chat_id, message in pairs:
        send_text(chat_id, message)
    return len(pairs)
