"""Find and score public Telegram channels/groups for the sourcing program.

For each public channel/group matching our keywords it collects: title, @username, link, type,
member count, description, posts/day and last post date, published admin contacts (@usernames,
emails, links found in the description), US-audience signal and promo rules. Scores them and
writes channels.csv (portal-importable). It does NOT scrape member lists or message anyone.

First run asks for your phone number and a login code (Telegram sends it to your app) - type them
in the terminal yourself; the session is saved locally in telegram_route/.

Usage:  python3 telegram_route/discover.py
        python3 telegram_route/discover.py --limit 10   # quicker test
"""
import argparse
import asyncio
import csv
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import config
from tg_client import get_client

HERE = Path(__file__).parent
OUT = HERE / "channels.csv"
FIELDS = ["title", "username", "link", "type", "members", "posts_per_day", "last_post_utc", "active",
          "us_signal", "promo_flag", "admin_contacts", "emails", "links", "keyword_hits", "score",
          "status", "description", "last_checked", "notes"]
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
HANDLE = re.compile(r"(?<![\w.])@([A-Za-z][A-Za-z0-9_]{4,31})")
URL = re.compile(r"(?:https?://|t\.me/)[^\s)>\]]+")


def any_match(patterns, text):
    return any(re.search(p, text, re.I) for p in patterns)


def us_signal(text):
    if any_match(config.US_PATTERNS, text):
        return "US"
    if any_match(config.NON_US_PATTERNS, text):
        return "Non-US"
    return "Unknown"


def promo_flag(text):
    if any_match(config.NO_PROMO_PATTERNS, text):
        return "NO_PROMO"
    if any_match(config.PROMO_OK_PATTERNS, text):
        return "PROMO_OK"
    return "UNKNOWN"


def score(members, ppd, us, promo, has_contact, hits, active):
    if promo == "NO_PROMO":
        return 0.0
    s = config.W_MEMBERS * math.log10(max(members, 1))
    s += config.W_POSTS_PER_DAY * min(ppd, config.POSTS_PER_DAY_CAP)
    s += config.BONUS_US if us == "US" else (-config.PENALTY_NON_US if us == "Non-US" else 0)
    s += config.BONUS_PROMO_OK if promo == "PROMO_OK" else 0
    s += config.BONUS_HAS_CONTACT if has_contact else 0
    s += config.BONUS_KEYWORD_HITS * min(hits, 4)
    return round(s if active else s / 2, 2)


async def activity(client, entity):
    dates = [m.date async for m in client.iter_messages(entity, limit=config.ACTIVITY_SAMPLE)]
    if not dates:
        return 0.0, None
    last = max(dates)
    if len(dates) < 2:
        return 0.0, last
    span = max((max(dates) - min(dates)).total_seconds() / 86400, 1 / 24)
    return round(len(dates) / span, 1), last


def load_existing():
    if not OUT.exists():
        return {}
    with OUT.open() as f:
        return {r["username"].lower(): r for r in csv.DictReader(f)}


async def run(limit):
    from telethon.tl.functions.contacts import SearchRequest
    from telethon.tl.functions.channels import GetFullChannelRequest
    from telethon.tl.types import Channel
    from telethon.errors import FloodWaitError

    client = get_client()
    await client.start()   # prompts for phone + code on first run (typed by you in the terminal)
    existing = load_existing()

    found = {}
    for kw in config.SEARCH_KEYWORDS:
        try:
            res = await client(SearchRequest(q=kw, limit=limit))
            for ch in res.chats:
                if isinstance(ch, Channel) and ch.username:
                    found.setdefault(ch.username.lower(), ch)
        except FloodWaitError as e:
            print(f"Telegram asked us to wait {e.seconds}s - pausing")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            print(f"search '{kw}' failed: {e}")
        await asyncio.sleep(config.SLEEP_BETWEEN_CALLS)
    for u in config.SEED_USERNAMES:
        try:
            ent = await client.get_entity(u)
            if isinstance(ent, Channel) and ent.username:
                found.setdefault(ent.username.lower(), ent)
        except Exception as e:
            print(f"seed @{u} not found: {e}")
    print(f"{len(found)} public channels/groups found")

    rows = []
    for key, ch in found.items():
        try:
            full = await client(GetFullChannelRequest(ch))
            members = full.full_chat.participants_count or 0
            if members < config.MIN_MEMBERS:
                continue
            about = (full.full_chat.about or "").replace("\n", " ")
            text = f"{ch.title} {about}"
            ppd, last = await activity(client, ch)
            active = bool(last and (datetime.now(timezone.utc) - last).days <= config.DEAD_DAYS)
            handles = sorted({h for h in HANDLE.findall(about) if h.lower() != key})
            emails = sorted(set(EMAIL.findall(about)))
            links = sorted(set(URL.findall(about)))
            us, promo = us_signal(text), promo_flag(about)
            hits = sum(1 for k in config.SEARCH_KEYWORDS if k.lower() in text.lower())
            prev = existing.get(key, {})
            rows.append({
                "title": ch.title, "username": ch.username, "link": f"https://t.me/{ch.username}",
                "type": "group" if ch.megagroup else "channel", "members": members,
                "posts_per_day": ppd, "last_post_utc": last.strftime("%Y-%m-%d") if last else "",
                "active": active, "us_signal": us, "promo_flag": promo,
                "admin_contacts": "; ".join("@" + h for h in handles), "emails": "; ".join(emails),
                "links": "; ".join(links[:5]), "keyword_hits": hits,
                "score": score(members, ppd, us, promo, bool(handles or emails), hits, active),
                "status": prev.get("status") or ("Skip - no promo" if promo == "NO_PROMO" else "New"),
                "description": about[:500], "last_checked": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "notes": prev.get("notes", ""),
            })
            print(f"  @{ch.username}: {members:,} members, {ppd}/day, {us}, {promo}")
        except FloodWaitError as e:
            print(f"Telegram asked us to wait {e.seconds}s - pausing")
            await asyncio.sleep(e.seconds + 5)
        except Exception as e:
            print(f"  @{ch.username}: skipped ({e.__class__.__name__})")
        await asyncio.sleep(config.SLEEP_BETWEEN_CALLS)

    await client.disconnect()
    rows.sort(key=lambda r: -float(r["score"]))
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {len(rows)} channels/groups to {OUT}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=config.SEARCH_LIMIT_PER_KEYWORD)
    asyncio.run(run(ap.parse_args().limit))


if __name__ == "__main__":
    main()
