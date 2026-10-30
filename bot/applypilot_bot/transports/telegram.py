"""Telegram transport using long polling (no public URL needed, ideal for development)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import httpx

from applypilot_bot.core import BotCore, Reply
from applypilot_bot.reminders import run_once

log = logging.getLogger(__name__)


@dataclass
class Incoming:
    chat_id: str
    text: str = ""
    file_id: str | None = None
    caption: str = ""


def parse_update(update: dict) -> Incoming | None:
    msg = update.get("message") or {}
    chat = msg.get("chat") or {}
    if "id" not in chat:
        return None
    chat_id = str(chat["id"])
    if msg.get("photo"):
        return Incoming(chat_id, file_id=msg["photo"][-1]["file_id"], caption=msg.get("caption", ""))  # largest size
    doc = msg.get("document") or {}
    if str(doc.get("mime_type", "")).startswith("image/"):
        return Incoming(chat_id, file_id=doc["file_id"], caption=msg.get("caption", ""))
    if msg.get("text"):
        return Incoming(chat_id, text=msg["text"])
    return None


class TelegramTransport:
    def __init__(self, token: str, core: BotCore, client: httpx.Client | None = None):
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        self.api = f"https://api.telegram.org/bot{token}"
        self.file_api = f"https://api.telegram.org/file/bot{token}"
        self.core = core
        self.http = client or httpx.Client(timeout=60.0)

    def send_text(self, chat_id: str, text: str) -> None:
        self.http.post(f"{self.api}/sendMessage", json={"chat_id": chat_id, "text": text[:4000]})

    def send_file(self, chat_id: str, data: bytes, filename: str, mime: str) -> None:
        # sendDocument keeps the exact bytes. sendPhoto would recompress and break the KB limits.
        self.http.post(f"{self.api}/sendDocument", data={"chat_id": chat_id}, files={"document": (filename, data, mime)})

    def _download(self, file_id: str) -> bytes:
        info = self.http.get(f"{self.api}/getFile", params={"file_id": file_id}).json()["result"]
        return self.http.get(f"{self.file_api}/{info['file_path']}").content

    def deliver(self, chat_id: str, replies: list[Reply]) -> None:
        for r in replies:
            if r.text:
                self.send_text(chat_id, r.text)
            if r.file:
                self.send_file(chat_id, *r.file)

    def handle(self, update: dict) -> None:
        inc = parse_update(update)
        if inc is None:
            return
        if inc.file_id:
            self.deliver(inc.chat_id, self.core.handle_image(inc.chat_id, self._download(inc.file_id), inc.caption))
        else:
            self.deliver(inc.chat_id, self.core.handle_text(inc.chat_id, inc.text))

    def run(self, reminder_days: int = 3) -> None:
        offset, last_reminder = 0, 0.0
        log.info("Telegram bot started")
        while True:
            try:
                res = self.http.get(f"{self.api}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=40).json()
                for update in res.get("result", []):
                    offset = update["update_id"] + 1
                    try:
                        self.handle(update)
                    except Exception:
                        log.exception("failed to handle update")
                if time.time() - last_reminder > 3600:
                    run_once(self.core.backend, self.core.store, reminder_days, self.send_text)
                    last_reminder = time.time()
            except httpx.HTTPError:
                log.warning("network problem, retrying")
                time.sleep(5)
