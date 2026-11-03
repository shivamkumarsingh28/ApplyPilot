"""WhatsApp Cloud API transport.

Needs a public HTTPS URL for the webhook. Business-initiated messages (such as
reminders) outside the 24-hour window require approved templates; this adapter
only replies to people who wrote first.
"""

from __future__ import annotations

import hashlib
import hmac
import logging

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request, Response

from applypilot_bot.core import BotCore, Reply

GRAPH = "https://graph.facebook.com/v20.0"
log = logging.getLogger(__name__)


def valid_signature(app_secret: str, body: bytes, header: str) -> bool:
    """Meta signs every webhook call with HMAC-SHA256 of the raw body. Reject anything else."""
    if not app_secret or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def extract_messages(payload: dict) -> list[dict]:
    out = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            out.extend(change.get("value", {}).get("messages", []))
    return out


class WhatsAppTransport:
    def __init__(self, core: BotCore, access_token: str, phone_number_id: str, verify_token: str, app_secret: str,
                 client: httpx.Client | None = None):
        self.core, self.phone_id, self.verify_token, self.app_secret = core, phone_number_id, verify_token, app_secret
        self.http = client or httpx.Client(timeout=60.0, headers={"Authorization": f"Bearer {access_token}"})

    def _check(self, resp: httpx.Response, what: str) -> httpx.Response:
        # Meta returns JSON errors (e.g. 190 = expired token). Without this check
        # a dead token looks like the bot silently ignored the user.
        if resp.is_error:
            log.error("WhatsApp %s failed: %s %s", what, resp.status_code, resp.text[:500])
            resp.raise_for_status()
        return resp

    def send_text(self, to: str, text: str) -> None:
        self._check(self.http.post(f"{GRAPH}/{self.phone_id}/messages", json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text[:4000]}}), "send_text")

    def send_file(self, to: str, data: bytes, filename: str, mime: str) -> None:
        up = self._check(self.http.post(f"{GRAPH}/{self.phone_id}/media", data={"messaging_product": "whatsapp"}, files={"file": (filename, data, mime)}), "upload media").json()
        self._check(self.http.post(f"{GRAPH}/{self.phone_id}/messages", json={"messaging_product": "whatsapp", "to": to, "type": "document", "document": {"id": up["id"], "filename": filename}}), "send_file")

    def _download(self, media_id: str) -> bytes:
        url = self._check(self.http.get(f"{GRAPH}/{media_id}"), "media url").json()["url"]
        return self._check(self.http.get(url), "media download").content

    def deliver(self, to: str, replies: list[Reply]) -> None:
        for r in replies:
            if r.text:
                self.send_text(to, r.text)
            if r.file:
                self.send_file(to, *r.file)

    def handle_message(self, msg: dict) -> None:
        sender = msg.get("from", "")
        if msg.get("type") == "text":
            self.deliver(sender, self.core.handle_text(sender, msg["text"]["body"]))
        elif msg.get("type") == "image":
            image = self._download(msg["image"]["id"])
            self.deliver(sender, self.core.handle_image(sender, image, msg["image"].get("caption", "")))
        elif msg.get("type") == "document":
            doc = msg["document"]
            data = self._download(doc["id"])
            replies = self.core.handle_document(sender, data, doc.get("filename", "notice.pdf"),
                                                doc.get("mime_type", ""), doc.get("caption", ""))
            self.deliver(sender, replies)
            done = self.core.poll_job(sender)
            if done:
                self.deliver(sender, done)

    def build_app(self) -> FastAPI:
        app = FastAPI(title="ApplyPilot WhatsApp webhook")

        @app.get("/health")
        def health():
            return {"status": "ok", "transport": "whatsapp", "phone_number_id_set": bool(self.phone_id)}

        @app.get("/webhook")
        def verify(request: Request):
            q = request.query_params
            if not self.verify_token:
                raise HTTPException(500, "WHATSAPP_VERIFY_TOKEN is not set")
            if q.get("hub.mode") == "subscribe" and hmac.compare_digest(q.get("hub.verify_token", ""), self.verify_token):
                return Response(q.get("hub.challenge", ""), media_type="text/plain")
            raise HTTPException(403, "Verification failed")

        @app.post("/webhook")
        async def receive(request: Request, background: BackgroundTasks):
            body = await request.body()
            if not self.app_secret:
                raise HTTPException(500, "WHATSAPP_APP_SECRET is not set")
            if not valid_signature(self.app_secret, body, request.headers.get("x-hub-signature-256", "")):
                raise HTTPException(403, "Bad signature")
            # Ack fast: Meta retries (and may disable) webhooks that answer slowly,
            # and handle_message calls the backend + Graph API synchronously.
            for msg in extract_messages(await request.json()):
                background.add_task(self._handle_safe, msg)
            return {"status": "ok"}

        return app

    def _handle_safe(self, msg: dict) -> None:
        try:
            self.handle_message(msg)
        except Exception:
            log.exception("WhatsApp handle_message failed for sender=%s", msg.get("from", ""))
