#!/usr/bin/env python3
"""Create a .env file with fresh random secrets. Safe to run again: it never overwrites an existing .env."""

import base64
import os
import secrets
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target, template = root / ".env", root / ".env.example"

if target.exists():
    print(".env already exists, leaving it alone.")
    sys.exit(0)

values = {
    "SECRET_KEY": secrets.token_urlsafe(48),
    "ENCRYPTION_KEY": base64.urlsafe_b64encode(os.urandom(32)).decode(),  # a valid Fernet key
    "BOT_SHARED_SECRET": secrets.token_urlsafe(24),
    "POSTGRES_PASSWORD": secrets.token_urlsafe(18),
}
lines = []
for line in template.read_text().splitlines():
    key = line.split("=", 1)[0].strip()
    if key in values and not line.lstrip().startswith("#"):
        comment = ""
        if "#" in line.split("=", 1)[1]:
            comment = "  #" + line.split("#", 1)[1]
        line = f"{key}={values[key]}{comment}"
    lines.append(line)
target.write_text("\n".join(lines) + "\n")
print("Created .env with new random secrets. Open it to choose your AI model (LLM_PROVIDER).")
