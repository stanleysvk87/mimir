#!/usr/bin/env python3
"""Weekly AI digest, delivered over Telegram.

Reads config from the same .env next to docker-compose.yml. Deliberately
NOT wired to any existing tg-bot service on the host -- this uses the
plain Telegram Bot API directly with its own token, so it stays a
generic, portable piece of the Mímir project instead of depending on an
unrelated service whose exact behavior isn't fully known.

Requires (in .env, both optional -- script is a silent no-op without them):
  MIMIR_TELEGRAM_BOT_TOKEN=...
  MIMIR_TELEGRAM_CHAT_ID=...
"""
import os
import sys
import urllib.request
import json
from pathlib import Path

MIMIR_URL = os.environ.get("MIMIR_URL", "http://127.0.0.1:8430")
MIMIR_PASSWORD = os.environ.get("MIMIR_PASSWORD", "")
BOT_TOKEN = os.environ.get("MIMIR_TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("MIMIR_TELEGRAM_CHAT_ID", "")


def _load_dotenv(path: Path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v)


def post_json(url, payload, headers=None):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json", **(headers or {})}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main():
    _load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    global BOT_TOKEN, CHAT_ID, MIMIR_PASSWORD
    BOT_TOKEN = os.environ.get("MIMIR_TELEGRAM_BOT_TOKEN", BOT_TOKEN)
    CHAT_ID = os.environ.get("MIMIR_TELEGRAM_CHAT_ID", CHAT_ID)
    MIMIR_PASSWORD = os.environ.get("MIMIR_PASSWORD", MIMIR_PASSWORD)

    if not BOT_TOKEN or not CHAT_ID:
        print("MIMIR_TELEGRAM_BOT_TOKEN / MIMIR_TELEGRAM_CHAT_ID not set -- skipping digest send.")
        return 0

    cookie_jar = urllib.request.HTTPCookieProcessor()
    opener = urllib.request.build_opener(cookie_jar)
    urllib.request.install_opener(opener)

    login_req = urllib.request.Request(
        f"{MIMIR_URL}/api/auth/login",
        data=json.dumps({"password": MIMIR_PASSWORD}).encode(),
        headers={"Content-Type": "application/json"},
    )
    urllib.request.urlopen(login_req, timeout=15)

    with urllib.request.urlopen(f"{MIMIR_URL}/api/ai/digest?days=7", timeout=60) as resp:
        digest = json.loads(resp.read())

    text = digest.get("digest", "(empty digest)")
    if digest.get("entry_count", 0) == 0:
        print("No entries this week -- not sending an empty digest.")
        return 0

    post_json(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        {"chat_id": CHAT_ID, "text": f"Mímir — your week:\n\n{text}"},
    )
    print("Digest sent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
