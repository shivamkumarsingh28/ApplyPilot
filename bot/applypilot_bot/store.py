"""Tiny SQLite store: which chat belongs to which ApplyPilot account, and which reminders were sent."""

import os
import sqlite3
from datetime import date


class Store:
    def __init__(self, path: str):
        if path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.execute("CREATE TABLE IF NOT EXISTS links (chat_id TEXT PRIMARY KEY, token TEXT NOT NULL)")
        self.db.execute("CREATE TABLE IF NOT EXISTS reminders (chat_id TEXT, app_id INTEGER, sent_on TEXT, PRIMARY KEY (chat_id, app_id, sent_on))")
        self.db.commit()

    def link(self, chat_id: str, token: str) -> None:
        self.db.execute("INSERT OR REPLACE INTO links VALUES (?, ?)", (chat_id, token))
        self.db.commit()

    def unlink(self, chat_id: str) -> None:
        self.db.execute("DELETE FROM links WHERE chat_id = ?", (chat_id,))
        self.db.commit()

    def token(self, chat_id: str) -> str | None:
        row = self.db.execute("SELECT token FROM links WHERE chat_id = ?", (chat_id,)).fetchone()
        return row[0] if row else None

    def all_chats(self) -> list[tuple[str, str]]:
        return self.db.execute("SELECT chat_id, token FROM links").fetchall()

    def reminded_today(self, chat_id: str, app_id: int) -> bool:
        return self.db.execute("SELECT 1 FROM reminders WHERE chat_id=? AND app_id=? AND sent_on=?", (chat_id, app_id, date.today().isoformat())).fetchone() is not None

    def mark_reminded(self, chat_id: str, app_id: int) -> None:
        self.db.execute("INSERT OR IGNORE INTO reminders VALUES (?, ?, ?)", (chat_id, app_id, date.today().isoformat()))
        self.db.commit()
