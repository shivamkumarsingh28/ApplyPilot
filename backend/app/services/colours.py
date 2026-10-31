"""Plain-word / hex background colours for the photo studio (Phase 2 step 7)."""
from __future__ import annotations

import re

COLOURS: dict[str, tuple[int, int, int]] = {
    "white": (255, 255, 255), "off white": (250, 250, 248), "light blue": (173, 216, 230),
    "sky blue": (135, 206, 235), "blue": (70, 130, 200), "dark blue": (30, 80, 160),
    "light grey": (220, 220, 220), "grey": (200, 200, 200), "gray": (200, 200, 200),
    "light gray": (220, 220, 220), "cream": (255, 253, 230), "light pink": (255, 220, 225),
    "pink": (255, 182, 193), "light green": (200, 235, 200), "beige": (245, 240, 220),
    "light yellow": (255, 250, 200),
}
_HEX = re.compile(r"^#?([0-9a-f]{6})$", re.I)


def parse_colour(value: str | None) -> tuple[tuple[int, int, int], str] | None:
    """'light blue' / '#e6f0ff' -> ((r,g,b), canonical name). None if unknown."""
    if not value:
        return None
    v = " ".join(str(value).strip().lower().replace("-", " ").replace("_", " ").split())
    if v in COLOURS:
        return COLOURS[v], v
    m = _HEX.match(v.replace(" ", ""))
    if m:
        h = m.group(1)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)), f"#{h.lower()}"
    return None


def resolve_background(requested: str | None, portal_rule: str | None) -> tuple[tuple[int, int, int], str, bool]:
    """Returns (rgb, label, overridden). A portal rule (e.g. 'white') always wins."""
    rule = parse_colour(portal_rule) if portal_rule else None
    req = parse_colour(requested) if requested else None
    if rule and req and rule[0] != req[0]:
        return rule[0], rule[1], True
    chosen = req or rule or ((255, 255, 255), "white")
    return chosen[0], chosen[1], False
