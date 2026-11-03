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
    "PDF — tell me what to do with it in the caption:\n"
    "- No caption (or 'notice'): I read it as a notice and answer questions about it.\n"
    "- 'save': I only save it to your vault. I do not read it.\n"
    "- 'compress' or 'compress 500kb': I shrink the PDF and send it back.\n\n"
    "Photo — I ONLY resize by default. I never change the background unless you ask.\n"
    "- 'resize 200x230' : exact pixels. 'compress 50kb' / 'under 100kb': max file size.\n"
    "- 'photo 3': use notice 3's photo rules (still no background change).\n"
    "- 'photo 3 blue background' or 'signature 3': full edit — only now I may change the background.\n"
    "I always show a preview first; reply 'yes' to keep it.\n\n"
    "Ask me things like:\n- What is the last date?\n- Am I eligible?\n- What photo size do I need?\n\n"
    "Commands: /deadlines  /notices  /use 3  /eligible  /link CODE  /unlink  /help\n\n"
    "Privacy tip: never send passwords or ID numbers in chat."
)

MAX_DOC_BYTES = 5 * 1024 * 1024
_DOB_RE = re.compile(r"^\s*(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\s*$")
_COLOUR_RE = re.compile(r"#(?:[0-9a-fA-F]{6})\b|\b(?:light blue|sky blue|dark blue|light grey|light gray|light pink|light green|light yellow|off white|white|blue|grey|gray|cream|pink|beige)\b", re.I)
_SIZE_RE = re.compile(r"(\d{2,5})\s*[x×]\s*(\d{2,5})", re.I)
_KB_RE = re.compile(r"(\d{1,5})\s*(kb|mb)\b", re.I)


def _kb_from_match(m: re.Match) -> int:
    value = int(m.group(1))
    return value * 1024 if m.group(2).lower() == "mb" else value


@dataclass
class ImageIntent:
    """What the caption asked for. Default: resize only, background untouched."""

    kind: str = "photo_resize"  # photo_resize | photo | signature | document
    notice_id: int | None = None
    width: int | None = None
    height: int | None = None
    min_kb: int | None = None
    max_kb: int | None = None
    background: str | None = None
    change_background: bool = False


def parse_image_intent(caption: str) -> ImageIntent:
    """Turn a photo caption into explicit instructions.

    The background is changed ONLY when the user names a background/colour or
    says 'background'. A bare 'photo 3' means 'use notice 3's size/KB rules',
    never 'repaint my background'.
    """
    text = (caption or "").lower()
    intent = ImageIntent()
    if re.search(r"\bsign", text):
        intent.kind = "signature"
    elif re.search(r"\b(document|certificate|marksheet|scan)\b", text):
        intent.kind = "document"
    elif re.search(r"\bphoto\b", text):
        intent.kind = "photo"  # portal mode (notice size/KB), background still opt-in
    size = _SIZE_RE.search(text)
    if size:
        intent.width, intent.height = int(size.group(1)), int(size.group(2))
    kbs = [_kb_from_match(m) for m in _KB_RE.finditer(text)]
    if re.search(r"\b(compress|reduce|shrink|under|max|maximum|below|less than)\b", text) and kbs:
        intent.max_kb = kbs[-1]
    elif len(kbs) >= 2:
        intent.min_kb, intent.max_kb = min(kbs), max(kbs)
    elif kbs and re.search(r"\b(min|minimum|at least)\b", text):
        intent.min_kb = kbs[0]
    colour = _COLOUR_RE.search(caption or "")
    # Background changes only on an explicit ask: '... blue background' or the
    # classic portal form 'photo 3 blue'. Never from a bare resize/compress.
    wants_bg = bool(colour) and ("background" in text or bool(re.search(r"\b(?:photo|signature)\s+#?\d+\s+\S+", text)))
    if wants_bg:
        intent.kind = "signature" if intent.kind == "signature" else "photo"
        intent.background = colour.group(0)
        intent.change_background = True
    m = re.search(r"#?(\d+)\b", text)
    # A leading notice number: 'photo 3', 'signature 3', '3'. Sizes/KB handled above.
    notice_match = re.search(r"(?:photo|signature|notice|doc(?:ument)?)?\s*#(\d+)\b|\b(?:photo|signature)\s+(\d+)\b", text)
    if notice_match:
        intent.notice_id = int(notice_match.group(1) or notice_match.group(2))
    elif m and not size and not kbs:
        intent.notice_id = int(m.group(1))
    return intent


@dataclass
class DocumentIntent:
    action: str = "notice"  # notice | save | compress
    max_kb: int | None = None


def parse_document_intent(caption: str, filename: str = "", mime: str = "") -> DocumentIntent:
    """A PDF is a notice ONLY by default/for 'notice' captions.

    'save'/'vault' = store untouched, 'compress ...kb' = shrink and return.
    Non-PDF documents (images sent as files, text) default to vault save.
    """
    text = (caption or "").lower()
    intent = DocumentIntent()
    if re.search(r"\b(compress|shrink|reduce)\b", text):
        intent.action = "compress"
        kbs = [_kb_from_match(m) for m in _KB_RE.finditer(text)]
        if kbs:
            intent.max_kb = kbs[-1]
        return intent
    if re.search(r"\b(save|vault|store|keep)\b", text):
        intent.action = "save"
        return intent
    if re.search(r"\bnotice\b", text):
        intent.action = "notice"
        return intent
    is_pdf = mime == "application/pdf" or filename.lower().endswith(".pdf")
    intent.action = "notice" if is_pdf else "save"
    return intent


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

    # -- documents (PDFs and files) -------------------------------------------
    def handle_document(self, chat_id: str, data: bytes, filename: str, mime: str, caption: str = "") -> list[Reply]:
        token = self.store.token(chat_id)
        if not token:
            return [Reply(LINK_HELP)]
        if len(data) > MAX_DOC_BYTES:
            return [Reply(f"That file is larger than {MAX_DOC_BYTES // (1024 * 1024)} MB. Please send a smaller file, "
                          "or compress it on the website first.")]
        intent = parse_document_intent(caption, filename, mime)
        try:
            if intent.action == "save":
                doc = self.backend.upload_document(token, data, filename, mime)
                return [Reply(f"Saved '{doc.get('filename', filename)}' to your vault. I did not read it as a notice. "
                              "To read a PDF as a notice, send it with the caption 'notice'.")]
            if intent.action == "compress":
                if mime != "application/pdf" and not filename.lower().endswith(".pdf"):
                    return [Reply("I can only compress PDFs this way. For a photo, send it as a picture with "
                                  "a caption like 'compress 100kb'.")]
                result = self.backend.compress_pdf(token, data, filename, intent.max_kb)
                info = result["report"]
                head = (f"Compressed: {info['original_kb']} KB → {info['final_kb']} KB ({info['pages']} pages, {info['method']}). "
                        "Also saved to your vault.")
                if intent.max_kb and not info["within"]:
                    head += f"\nI could not reach {intent.max_kb} KB without damaging the pages; this is the smallest safe copy."
                return [Reply(head), Reply(file=(result["bytes"], result["filename"], result["mime"]))]
            job = self.backend.upload_notice(token, data, filename, mime)
        except BackendError as exc:
            return [self._error(chat_id, exc)]
        self.store.set_state(chat_id, "job_id", str(job["job_id"]))
        return [Reply("Got it, reading your notice. I will message you when it is ready. "
                      "(Tip: caption 'save' = vault only, 'compress 500kb' = shrink the PDF.)")]

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
        intent = parse_image_intent(caption)
        notice_id = intent.notice_id
        try:
            if notice_id is None and (intent.width is None and intent.max_kb is None and intent.kind in ("photo", "signature")):
                notice_id = self._current_notice(chat_id, token)
                if notice_id is None and len(self.backend.notices(token)) > 1:
                    notices = self.backend.notices(token)
                    listing = "\n".join(f"#{n['id']} {n['title'][:50]}" for n in notices[:8])
                    return [Reply(f"Which notice is this for? Send the picture again with a caption like 'photo {notices[0]['id']}', "
                                  f"or just say the size, for example 'resize 200x230' or 'compress 50kb'.\n\n{listing}")]
            result = self.backend.photo(token, image, intent.kind, notice_id, intent.background,
                                        intent.width, intent.height, intent.min_kb, intent.max_kb,
                                        intent.change_background)
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
        if intent.change_background:
            note = ""
        elif notice_id:
            note = f"\nUsed notice #{notice_id}'s size/KB rules. Background NOT changed (say e.g. 'photo {notice_id} blue background' to change it)."
        elif intent.width or intent.max_kb:
            note = "\nResized only — background NOT changed."
        else:
            note = "\nNo size was given, so only the file size was optimised. Background NOT changed. Try 'resize 200x230' or 'compress 50kb'."
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
