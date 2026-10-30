"""Chat logic shared by every messaging app.

A transport (Telegram, WhatsApp) turns an incoming message into `handle_text` or
`handle_image` calls and sends the returned `Reply` objects back. All rules live
here, so a new transport only needs to read and write messages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from applypilot_bot.api_client import Backend, BackendError
from applypilot_bot.store import Store

HELP = (
    "I can help with your job and admission notices.\n\n"
    "Ask me things like:\n- What is the last date?\n- Am I eligible?\n- What photo size do I need?\n\n"
    "Send a photo or signature picture with the caption 'photo 3' or 'signature 3' (3 is your notice number) "
    "and I will resize it to match.\n\n"
    "Commands: /deadlines  /link CODE  /unlink  /help\n\n"
    "Privacy tip: never send passwords or ID numbers in chat."
)
LINK_HELP = "First link your account: open the ApplyPilot website, go to Profile, press 'Create link code', then send me /link CODE."


@dataclass
class Reply:
    text: str | None = None
    file: tuple[bytes, str, str] | None = None  # (bytes, filename, mime)


class BotCore:
    def __init__(self, backend: Backend, store: Store):
        self.backend, self.store = backend, store

    # -- text ---------------------------------------------------------------
    def handle_text(self, chat_id: str, text: str) -> list[Reply]:
        text = (text or "").strip()
        cmd, _, arg = text.partition(" ")
        cmd = cmd.lower().split("@")[0]
        if cmd in ("/start", "/help"):
            return [Reply(HELP if self.store.token(chat_id) else "Welcome to ApplyPilot!\n\n" + LINK_HELP)]
        if cmd == "/link":
            return self._link(chat_id, arg.strip())
        if cmd == "/unlink":
            self.store.unlink(chat_id)
            return [Reply("Your chat is unlinked.")]
        token = self.store.token(chat_id)
        if not token:
            return [Reply(LINK_HELP)]
        try:
            if cmd == "/deadlines":
                return [Reply(self._format_deadlines(self.backend.deadlines(token)))]
            return [Reply(self.backend.chat(token, text)["answer"])]
        except BackendError as exc:
            return [self._error(chat_id, exc)]

    def _link(self, chat_id: str, code: str) -> list[Reply]:
        if not code:
            return [Reply("Send /link and the code from the website, for example: /link A1B2C3D4")]
        try:
            self.store.link(chat_id, self.backend.link(code.upper(), chat_id))
        except BackendError as exc:
            return [Reply(f"Could not link: {exc.detail}")]
        return [Reply("Linked! Ask me about your notices, or send /help.")]

    @staticmethod
    def _format_deadlines(rows: list[dict]) -> str:
        if not rows:
            return "No open applications are due in the next 14 days."
        return "Due soon:\n" + "\n".join(f"- {r['title'][:60]}: {r['deadline']} ({r['days_left']} days left)" for r in rows)

    def _error(self, chat_id: str, exc: BackendError) -> Reply:
        if exc.status == 401:
            self.store.unlink(chat_id)
            return Reply("Your session ended. " + LINK_HELP)
        if exc.status == 429:
            return Reply("You are asking too fast. Please wait a minute.")
        return Reply(f"Sorry, something went wrong: {exc.detail}")

    # -- images -------------------------------------------------------------
    def handle_image(self, chat_id: str, image: bytes, caption: str = "") -> list[Reply]:
        token = self.store.token(chat_id)
        if not token:
            return [Reply(LINK_HELP)]
        kind = "signature" if re.search(r"sign", caption or "", re.I) else "photo"
        m = re.search(r"#?(\d+)", caption or "")
        notice_id = int(m.group(1)) if m else None
        try:
            if notice_id is None:
                notices = self.backend.notices(token)
                if len(notices) == 1:
                    notice_id = notices[0]["id"]
                elif len(notices) > 1:
                    listing = "\n".join(f"#{n['id']} {n['title'][:50]}" for n in notices[:8])
                    return [Reply(f"Which notice is this for? Send the picture again with a caption like '{kind} {notices[0]['id']}'.\n\n{listing}")]
            result = self.backend.photo(token, image, kind, notice_id)
        except BackendError as exc:
            return [self._error(chat_id, exc)]
        report = result["report"]
        lines = [("OK " if c["ok"] else "CHECK ") + f"{c['name']}: {c['detail']}" for c in report["checks"]] + report["warnings"]
        head = "Your file is ready." if report["ok"] else "I made the file, but please check the items below."
        note = "" if notice_id else "\nNo notice was chosen, so I used default sizes."
        return [Reply(f"{head}{note}\n" + "\n".join(lines) + "\nSaved to your vault too."),
                Reply(file=(result["bytes"], result["filename"], result["mime"]))]
