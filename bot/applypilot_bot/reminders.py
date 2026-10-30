"""Sends one reminder per application per day for deadlines that are close."""

from __future__ import annotations

from collections.abc import Callable

from applypilot_bot.api_client import Backend, BackendError
from applypilot_bot.store import Store


def due_reminders(backend: Backend, store: Store, days: int) -> list[tuple[str, str]]:
    """Returns (chat_id, message) pairs that have not been sent today."""
    out: list[tuple[str, str]] = []
    for chat_id, token in store.all_chats():
        try:
            rows = backend.deadlines(token, days)
        except BackendError:
            continue
        for row in rows:
            if store.reminded_today(chat_id, row["id"]):
                continue
            out.append((chat_id, f"Reminder: {row['title'][:60]} closes on {row['deadline']} ({row['days_left']} days left)."))
            store.mark_reminded(chat_id, row["id"])
    return out


def run_once(backend: Backend, store: Store, days: int, send_text: Callable[[str, str], None]) -> int:
    pairs = due_reminders(backend, store, days)
    for chat_id, message in pairs:
        send_text(chat_id, message)
    return len(pairs)
