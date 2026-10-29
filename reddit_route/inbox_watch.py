"""Watch the inbox for modmail replies and update statuses.

Any reply from a subreddit we messaged sets its status to "Replied - review" (or "Declined" when the
reply reads like a no), records the reply in replies.csv, and stops all follow-up for that subreddit.
Read-only on Reddit: it never sends anything.

Usage:  python3 reddit_route/inbox_watch.py           # check once
        python3 reddit_route/inbox_watch.py --loop 30 # check every 30 minutes
"""
import argparse
import csv
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from reddit_client import get_reddit

HERE = Path(__file__).parent
SUBS = HERE / "subreddits.csv"
REPLIES = HERE / "replies.csv"
REPLY_FIELDS = ["date_utc", "subreddit", "from", "subject", "body", "classified_as", "message_id"]
DECLINE = re.compile(r"\b(not allowed|no thanks|not interested|decline|can'?t allow|against (our|the) rules|removed|banned)\b", re.I)


def seen_ids():
    if not REPLIES.exists():
        return set()
    with REPLIES.open() as f:
        return {r["message_id"] for r in csv.DictReader(f)}


def check(reddit):
    with SUBS.open() as f:
        rows = list(csv.DictReader(f))
    by_name = {r["subreddit"].lower(): r for r in rows}
    seen, new = seen_ids(), []
    for msg in reddit.inbox.all(limit=100):
        mid = getattr(msg, "id", "")
        sub = getattr(msg, "subreddit", None)
        if not sub or mid in seen:
            continue
        row = by_name.get(str(sub).lower())
        if not row or row["status"] not in ("Messaged", "Replied - review"):
            continue
        body = getattr(msg, "body", "") or ""
        cls = "Declined" if DECLINE.search(body) else "Replied - review"
        row["status"] = cls
        new.append({"date_utc": datetime.fromtimestamp(msg.created_utc, timezone.utc).strftime("%Y-%m-%d %H:%M"),
                    "subreddit": row["subreddit"], "from": str(getattr(msg, "author", "") or sub),
                    "subject": getattr(msg, "subject", ""), "body": body[:1000],
                    "classified_as": cls, "message_id": mid})
    if new:
        first = not REPLIES.exists()
        with REPLIES.open("a", newline="") as f:
            w = csv.DictWriter(f, fieldnames=REPLY_FIELDS)
            if first:
                w.writeheader()
            w.writerows(new)
        with SUBS.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"{datetime.now():%H:%M} - {len(new)} new replies" + "".join(f"\n  r/{n['subreddit']}: {n['classified_as']}" for n in new))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", type=int, default=0, help="minutes between checks (0 = run once)")
    args = ap.parse_args()
    if not SUBS.exists():
        raise SystemExit("subreddits.csv not found - run discover.py first.")
    reddit = get_reddit(need_login=True)
    while True:
        check(reddit)
        if not args.loop:
            break
        time.sleep(args.loop * 60)


if __name__ == "__main__":
    main()
