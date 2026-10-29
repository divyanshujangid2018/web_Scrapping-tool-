"""Shared Telethon client built from telegram_route/.env (never hard-code secrets)."""
import os
import sys
from pathlib import Path

HERE = Path(__file__).parent


def load_env(path=HERE / ".env"):
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_client():
    try:
        from telethon import TelegramClient
    except ImportError:
        sys.exit("Telethon is not installed. Run: pip3 install -r telegram_route/requirements.txt")
    load_env()
    api_id, api_hash = os.getenv("TG_API_ID"), os.getenv("TG_API_HASH")
    if not api_id or not api_hash:
        sys.exit("Missing TG_API_ID / TG_API_HASH in telegram_route/.env (see .env.example).")
    # The session file is created on first login and stores your login locally - keep it private.
    session = str(HERE / os.getenv("TG_SESSION_NAME", "sourcing_session"))
    return TelegramClient(session, int(api_id), api_hash)
