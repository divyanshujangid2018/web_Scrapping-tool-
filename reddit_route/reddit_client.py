"""Shared PRAW client, built from credentials in .env (never hard-code secrets)."""
import os
import sys
from pathlib import Path


def load_env(path=Path(__file__).with_name(".env")):
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def get_reddit(need_login=False):
    try:
        import praw
    except ImportError:
        sys.exit("PRAW is not installed. Run: pip3 install -r reddit_route/requirements.txt")
    load_env()
    cid, secret = os.getenv("REDDIT_CLIENT_ID"), os.getenv("REDDIT_CLIENT_SECRET")
    agent = os.getenv("REDDIT_USER_AGENT", "multiapp-sourcing/0.1")
    if not cid or not secret:
        sys.exit("Missing REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET in reddit_route/.env (see .env.example).")
    if need_login:
        user, pw = os.getenv("REDDIT_USERNAME"), os.getenv("REDDIT_PASSWORD")
        if not user or not pw:
            sys.exit("Sending/reading modmail needs REDDIT_USERNAME and REDDIT_PASSWORD in reddit_route/.env.")
        return praw.Reddit(client_id=cid, client_secret=secret, user_agent=agent, username=user, password=pw)
    return praw.Reddit(client_id=cid, client_secret=secret, user_agent=agent)
