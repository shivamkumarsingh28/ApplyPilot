"""Foreground segmentation used by the photo studio.

`OpenCVSegmenter` (GrabCut) works offline. `MetaSamSegmenter` calls SAM 3.1 over
HTTP; Meta announced SAM 3.1 on the Meta Model API, but its request/response
format is not something this project could verify, so the adapter expects a
simple contract you can match with a thin proxy: POST {image: base64, prompt}
and receive {mask: base64 PNG}. `FallbackSegmenter` guarantees that a failing
remote call never breaks the user's upload.
"""

from __future__ import annotations

import base64
import io
import logging
from abc import ABC, abstractmethod
from functools import lru_cache

import cv2
import httpx
import numpy as np
from PIL import Image

from app.core.config import get_settings

log = logging.getLogger(__name__)


class Segmenter(ABC):
    name = "base"

    @abstractmethod
    def foreground_mask(self, image: Image.Image, hint_box: tuple[int, int, int, int] | None, prompt: str) -> np.ndarray:
        """Return a uint8 mask (H, W) with 255 for the foreground subject."""


class OpenCVSegmenter(Segmenter):
    name = "opencv-grabcut"

    def foreground_mask(self, image, hint_box, prompt="person"):
        rgb = np.array(image.convert("RGB"))
        h, w = rgb.shape[:2]
        mask = np.zeros((h, w), np.uint8)
        if hint_box:
            x, y, bw, bh = hint_box
        else:
            x, y, bw, bh = int(w * 0.1), int(h * 0.05), int(w * 0.8), int(h * 0.9)
        rect = (max(1, x), max(1, y), max(2, min(bw, w - x - 1)), max(2, min(bh, h - y - 1)))
        bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
        try:
            cv2.grabCut(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), mask, rect, bgd, fgd, 4, cv2.GC_INIT_WITH_RECT)
        except cv2.error:
            return np.full((h, w), 255, np.uint8)
        return np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)


class MetaSamSegmenter(Segmenter):
    name = "sam-3.1-http"

    def __init__(self, endpoint: str, api_key: str = "", timeout: float = 60.0):
        self.endpoint = endpoint
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.timeout = timeout

    def foreground_mask(self, image, hint_box, prompt="person"):
        buf = io.BytesIO()
        image.convert("RGB").save(buf, format="JPEG", quality=92)
        body = {"image": base64.b64encode(buf.getvalue()).decode(), "prompt": prompt}
        resp = httpx.post(self.endpoint, json=body, headers=self.headers, timeout=self.timeout)
        resp.raise_for_status()
        mask = Image.open(io.BytesIO(base64.b64decode(resp.json()["mask"]))).convert("L").resize(image.size)
        return np.where(np.array(mask) > 127, 255, 0).astype(np.uint8)


class FallbackSegmenter(Segmenter):
    def __init__(self, primary: Segmenter, fallback: Segmenter):
        self.primary, self.fallback = primary, fallback
        self.name = primary.name
        self.last_used = primary.name

    def foreground_mask(self, image, hint_box, prompt="person"):
        try:
            mask = self.primary.foreground_mask(image, hint_box, prompt)
            self.last_used = self.primary.name
            return mask
        except Exception as exc:
            log.warning("segmenter %s failed (%s); using %s", self.primary.name, exc, self.fallback.name)
            self.last_used = self.fallback.name
            return self.fallback.foreground_mask(image, hint_box, prompt)


@lru_cache
def get_segmenter() -> Segmenter:
    s = get_settings()
    if s.segmenter == "meta_sam" and s.sam_endpoint:
        return FallbackSegmenter(MetaSamSegmenter(s.sam_endpoint, s.sam_api_key), OpenCVSegmenter())
    return OpenCVSegmenter()
