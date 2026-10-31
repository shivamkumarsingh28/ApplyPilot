"""Talks to the ApplyPilot backend on behalf of one linked chat."""

import base64

import httpx


class BackendError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


class Backend:
    def __init__(self, base_url: str, bot_secret: str, transport: httpx.BaseTransport | None = None):
        self.base = base_url.rstrip("/") + "/api/v1"
        self.secret = bot_secret
        self.http = httpx.Client(timeout=120.0, transport=transport)

    def _send(self, method: str, path: str, token: str | None = None, **kw):
        headers = kw.pop("headers", {})
        if token:
            headers["Authorization"] = f"Bearer {token}"
        res = self.http.request(method, self.base + path, headers=headers, **kw)
        if res.status_code >= 400:
            try:
                detail = res.json().get("detail", res.text)
            except ValueError:
                detail = res.text
            raise BackendError(res.status_code, str(detail))
        return res.json()

    def link(self, code: str, chat_id: str) -> str:
        data = self._send("POST", "/bot/link", json={"code": code, "chat_id": chat_id}, headers={"X-Bot-Secret": self.secret})
        return data["access_token"]

    def chat(self, token: str, message: str, notice_id: int | None = None) -> dict:
        return self._send("POST", "/assistant/chat", token, json={"message": message, "notice_id": notice_id})

    def deadlines(self, token: str, days: int = 14) -> list[dict]:
        return self._send("GET", f"/applications/upcoming?days={days}", token)

    def notices(self, token: str) -> list[dict]:
        return self._send("GET", "/notices", token)

    def photo(self, token: str, image: bytes, kind: str, notice_id: int | None, background: str | None = None) -> dict:
        data = {"kind": kind, "save_to_vault": "true"}
        if notice_id:
            data["notice_id"] = str(notice_id)
        if background:
            data["background"] = background
        res = self._send("POST", "/photo/process", token, data=data, files={"file": ("upload.jpg", image, "image/jpeg")})
        res["bytes"] = base64.b64decode(res["data_base64"])
        return res

    def upload_notice(self, token: str, data: bytes, filename: str, mime: str) -> dict:
        return self._send("POST", "/jobs/ingest", token, data={"source": "bot"},
                          files={"file": (filename, data, mime or "application/octet-stream")})

    def job(self, token: str, job_id: int) -> dict:
        return self._send("GET", f"/jobs/{job_id}", token)

    def profile(self, token: str) -> dict:
        return self._send("GET", "/profile", token)

    def save_profile(self, token: str, data: dict) -> dict:
        return self._send("PUT", "/profile", token, json=data)

    def eligibility(self, token: str, notice_id: int) -> dict:
        return self._send("GET", f"/notices/{notice_id}/eligibility", token)
