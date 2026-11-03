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

    def deadlines(self, token: str, days: int = 14, milestones: str = "") -> list[dict]:
        if milestones:
            return self._send("GET", f"/applications/upcoming?milestones={milestones}", token)
        return self._send("GET", f"/applications/upcoming?days={days}", token)

    def notices(self, token: str) -> list[dict]:
        return self._send("GET", "/notices", token)

    def photo(self, token: str, image: bytes, kind: str = "photo_resize", notice_id: int | None = None,
              background: str | None = None, width: int | None = None, height: int | None = None,
              min_kb: int | None = None, max_kb: int | None = None, change_background: bool = False) -> dict:
        # Default kind is photo_resize: pixels + KB only, background untouched.
        # Full "photo" mode (face crop + background change) is opt-in only.
        data: dict[str, str] = {"kind": kind, "save_to_vault": "true", "change_background": str(change_background).lower()}
        if notice_id:
            data["notice_id"] = str(notice_id)
        if background:
            data["background"] = background
        for key, value in (("width", width), ("height", height), ("min_kb", min_kb), ("max_kb", max_kb)):
            if value:
                data[key] = str(value)
        res = self._send("POST", "/photo/process", token, data=data, files={"file": ("upload.jpg", image, "image/jpeg")})
        res["bytes"] = base64.b64decode(res["data_base64"])
        return res

    def upload_document(self, token: str, data: bytes, filename: str, mime: str, kind: str = "other") -> dict:
        return self._send("POST", "/documents", token, data={"kind": kind},
                          files={"file": (filename, data, mime or "application/octet-stream")})

    def compress_pdf(self, token: str, data: bytes, filename: str, max_kb: int | None = None) -> dict:
        form: dict[str, str] = {"save_to_vault": "true"}
        if max_kb:
            form["max_kb"] = str(max_kb)
        res = self._send("POST", "/pdf/compress", token, data=form, files={"file": (filename, data, "application/pdf")})
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
