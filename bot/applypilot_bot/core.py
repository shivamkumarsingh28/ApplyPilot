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
    "Send me a notice PDF and I will read it, then answer your questions about it.\n"
    "Ask me things like:\n- What is the last date?\n- Am I eligible?\n- What photo size do I need?\n\n"
    "Send a photo or signature picture with the caption 'photo 3' or 'signature 3' (3 is your notice number). "
    "Add a colour like 'photo 3 light blue' or 'photo 3 #e6f0ff'. I will show a preview first.\n\n"
    "Commands: /deadlines  /notices  /use 3  /eligible  /link CODE  /unlink  /help\n\n"
    "Privacy tip: never send passwords or ID numbers in chat."
)

MAX_DOC_BYTES = 5 * 1024 * 1024
_DOB_RE = re.compile(r"^\s*(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\s*$")
_COLOUR_RE = re.compile(r"#(?:[0-9a-fA-F]{6})\b|\b(?:light blue|sky blue|dark blue|light grey|light gray|light pink|light green|light yellow|off white|white|blue|grey|gray|cream|pink|beige)\b", re.I)


def split_text(text: str, limit: int = 1000) -> list[str]:
    """Chat apps cut long messages; split on line/sentence boundaries (plan 4.1)."""
    if len(text) <= limit:
        return [text]
    out, cur = [], ""
    for part in re.split(r"(?<=[.!?])\s+|\n", text):
        if cur and len(cur) + len(part) + 1 > limit:
            out.append(cur)
            cur = part
        else:
            cur = f"{cur} {part}".strip() if cur else part
    if cur:
        out.append(cur)
    return out or [text[:limit]]
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
            # Pending conversational states first: DOB answer, photo confirm.
            if self.store.get_state(chat_id, "awaiting_dob"):
                m = _DOB_RE.match(text)
                if m:
                    return self._save_dob(chat_id, token, m)
                return [Reply("Please send your date of birth as DD/MM/YYYY, for example 05/08/2004.")]
            if self.store.get_state(chat_id, "pending_photo"):
                if text.lower() in ("yes", "y"):
                    return self._confirm_photo(chat_id, token)
                if text.lower() in ("no", "n"):
                    self.store.clear_state(chat_id, "pending_photo")
                    return [Reply("Okay, discarded. Send the picture again with a different colour if you like.")]
            if cmd == "/deadlines":
                return [Reply(self._format_deadlines(self.backend.deadlines(token)))]
            if cmd == "/notices":
                rows = self.backend.notices(token)
                if not rows:
                    return [Reply("You have no notices yet. Send me a notice PDF to start.")]
                return [Reply("Your notices:\n" + "\n".join(f"#{n['id']} {n['title'][:60]}" for n in rows[:10])
                              + "\nSend /use NUMBER to pick one.")]
            if cmd == "/use":
                if not arg.strip().isdigit():
                    return [Reply("Send /use and the notice number, for example /use 3")]
                self.store.set_state(chat_id, "notice_id", arg.strip())
                return [Reply(f"Okay, I will use notice #{arg.strip()} for your questions.")]
            if cmd in ("/eligible", "/eligibility"):
                return self._eligibility(chat_id, token)
            notice_id = self._current_notice(chat_id, token)
            answer = self.backend.chat(token, text, notice_id)["answer"]
            return [Reply(p) for p in split_text(answer)]
        except BackendError as exc:
            return [self._error(chat_id, exc)]

    def _current_notice(self, chat_id: str, token: str) -> int | None:
        saved = self.store.get_state(chat_id, "notice_id")
        if saved and saved.isdigit():
            return int(saved)
        rows = self.backend.notices(token)
        if len(rows) == 1:
            return rows[0]["id"]
        return None

    def _eligibility(self, chat_id: str, token: str) -> list[Reply]:
        notice_id = self._current_notice(chat_id, token)
        if notice_id is None:
            return [Reply("Which notice? Send /notices, then /use NUMBER.")]
        result = self.backend.eligibility(token, notice_id)
        if "dob" in result.get("missing_profile_fields", []):
            self.store.set_state(chat_id, "awaiting_dob", "1")
            return [Reply("Please send your date of birth (DD/MM/YYYY). I keep it private and use it only for age checks.")]
        lines = [f"Eligibility for notice #{notice_id}: {result['verdict'].replace('_', ' ')}"]
        lines += [f"- {c['rule']}: {c['detail']}" for c in result.get("checks", [])]
        lines.append("Always confirm with the official notice.")
        return [Reply(p) for p in split_text("\n".join(lines))]

    def _save_dob(self, chat_id: str, token: str, m: re.Match) -> list[Reply]:
        from datetime import date

        try:
            dob = date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return [Reply("That date does not exist. Please send it as DD/MM/YYYY.")]
        profile = self.backend.profile(token)
        profile["dob"] = dob.isoformat()
        self.backend.save_profile(token, profile)
        self.store.clear_state(chat_id, "awaiting_dob")
        return [Reply(f"Saved your date of birth as {dob.strftime('%d/%m/%Y')}. Now send /eligible to check.")]

    # -- documents (notice PDFs) ---------------------------------------------
    def handle_document(self, chat_id: str, data: bytes, filename: str, mime: str, caption: str = "") -> list[Reply]:
        token = self.store.token(chat_id)
        if not token:
            return [Reply(LINK_HELP)]
        if len(data) > MAX_DOC_BYTES:
            return [Reply("That file is larger than 5 MB. Please send a smaller file.")]
        try:
            job = self.backend.upload_notice(token, data, filename, mime)
        except BackendError as exc:
            return [self._error(chat_id, exc)]
        self.store.set_state(chat_id, "job_id", str(job["job_id"]))
        return [Reply("Got it, reading your notice. I will message you when it is ready.")]

    def poll_job(self, chat_id: str) -> list[Reply]:
        """Transports call this after handle_document (and may poll). Returns [] until ready."""
        token = self.store.token(chat_id)
        job_id = self.store.get_state(chat_id, "job_id")
        if not token or not job_id:
            return []
        try:
            job = self.backend.job(token, int(job_id))
        except BackendError:
            return []
        if job["status"] in ("queued", "reading", "indexing"):
            return [Reply(f"Still {job['status']} your notice…")]
        self.store.clear_state(chat_id, "job_id")
        if job["status"] == "failed":
            return [Reply(f"I could not read that notice: {job.get('error') or 'unknown error'}")]
        if job.get("notice_id"):
            self.store.set_state(chat_id, "notice_id", str(job["notice_id"]))
        lines = [f"Your notice is ready: {job.get('title') or 'Notice'}"]
        lines += job.get("summary") or []
        lines.append("Ask me anything about it, for example: What is the last date?")
        return [Reply("\n".join(lines))]

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
        colour = _COLOUR_RE.search(caption or "")
        background = colour.group(0) if colour else None
        try:
            if notice_id is None:
                notice_id = self._current_notice(chat_id, token)
                if notice_id is None and len(self.backend.notices(token)) > 1:
                    notices = self.backend.notices(token)
                    listing = "\n".join(f"#{n['id']} {n['title'][:50]}" for n in notices[:8])
                    return [Reply(f"Which notice is this for? Send the picture again with a caption like '{kind} {notices[0]['id']}'.\n\n{listing}")]
            result = self.backend.photo(token, image, kind, notice_id, background)
        except BackendError as exc:
            return [self._error(chat_id, exc)]
        # Preview-then-confirm (plan 4.2): stash the file, send it, final copy on "yes".
        import base64
        import json as _json

        self.store.set_state(chat_id, "pending_photo", _json.dumps(
            {"b64": base64.b64encode(result["bytes"]).decode(), "filename": result["filename"], "mime": result["mime"]}))
        report = result["report"]
        lines = [("OK " if c["ok"] else "CHECK ") + f"{c['name']}: {c['detail']}" for c in report["checks"]] + report["warnings"]
        head = "Here is a preview. " + ("It passes the checks. " if report["ok"] else "Please check the items below. ")
        note = "" if notice_id else "\nNo notice was chosen, so I used default sizes."
        return [Reply(f"{head}{note}\n" + "\n".join(lines) + "\nReply 'yes' to keep it (saved to your vault), or 'no' to discard."),
                Reply(file=(result["bytes"], result["filename"], result["mime"]))]

    def _confirm_photo(self, chat_id: str, token: str) -> list[Reply]:
        import base64
        import json as _json

        raw = self.store.get_state(chat_id, "pending_photo")
        self.store.clear_state(chat_id, "pending_photo")
        try:
            data = _json.loads(raw or "{}")
            payload = base64.b64decode(data["b64"])
        except Exception:
            return [Reply("That preview expired. Please send the picture again.")]
        return [Reply("Saved to your vault. Here is the final file — send it as-is (do not recompress it)."),
                Reply(file=(payload, data.get("filename", "photo_ready.jpg"), data.get("mime", "image/jpeg")))]
