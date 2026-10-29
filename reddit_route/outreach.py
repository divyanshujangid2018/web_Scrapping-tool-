"""Step 2 - message subreddit moderators via modmail (dry run by default).

Picks the highest-scoring subreddits from subreddits.csv that are not rule-forbidden and not yet
contacted, personalises the message, and sends at most DAILY_SEND_CAP modmails with random delays.
Every send is logged in outreach_log.csv and the subreddit's status becomes "Messaged", so the
same subreddit is never messaged twice.

Usage:  python3 reddit_route/outreach.py              # DRY RUN: prints messages, sends nothing
        python3 reddit_route/outreach.py --send       # actually sends (respects the daily cap)
        python3 reddit_route/outreach.py --send --only beermoney,WorkOnline
        python3 reddit_route/outreach.py --manual     # no API sending: writes outreach_manual.csv with
                                                      # one-click modmail links you open and send yourself
"""
import argparse
import csv
import random
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import config
from reddit_client import get_reddit

HERE = Path(__file__).parent
SUBS = HERE / "subreddits.csv"
LOG = HERE / "outreach_log.csv"
LOG_FIELDS = ["date_utc", "subreddit", "subject", "status", "error"]


def read_subs():
    if not SUBS.exists():
        raise SystemExit("subreddits.csv not found - run discover.py first.")
    with SUBS.open() as f:
        return list(csv.DictReader(f))


def write_subs(rows):
    with SUBS.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def sent_today():
    if not LOG.exists():
        return 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with LOG.open() as f:
        return sum(1 for r in csv.DictReader(f) if r["date_utc"].startswith(today) and r["status"] == "Sent")


def log(entry):
    new = not LOG.exists()
    with LOG.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if new:
            w.writeheader()
        w.writerow(entry)


def build_message(row):
    note = ""
    if row["rules_flag"] == "MODS_FIRST":
        note = f" (your rules ask that this kind of request goes to the mods first: {row['flagged_rules']})"
    subs_k = max(1, round(int(row["subscribers"]) / 1000))
    fill = dict(subreddit=row["subreddit"], subscribers_k=subs_k, rule_note=note,
                sender_name=config.SENDER_NAME, company=config.COMPANY)
    return config.SUBJECT.format(**fill)[:100], config.MESSAGE.format(**fill)


def write_manual(rows, only_arg=""):
    """Prefilled modmail compose links (you review and press Send in your own browser)."""
    only = {s.strip().lower() for s in only_arg.split(",") if s.strip()}
    queue = [r for r in rows if r["rules_flag"] != "FORBID" and r["status"] == "New"
             and float(r["score"]) >= config.MIN_SCORE_TO_CONTACT and (not only or r["subreddit"].lower() in only)]
    queue.sort(key=lambda r: -float(r["score"]))
    out = HERE / "outreach_manual.csv"
    with out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subreddit", "score", "rules_flag", "flagged_rules", "mod_usernames", "rules_url", "modmail_link", "subject", "message"])
        for r in queue:
            subject, body = build_message(r)
            link = "https://old.reddit.com/message/compose?" + urllib.parse.urlencode(
                {"to": f"/r/{r['subreddit']}", "subject": subject, "message": body})
            w.writerow([r["subreddit"], r["score"], r["rules_flag"], r["flagged_rules"], r["mod_usernames"],
                        f"https://www.reddit.com/r/{r['subreddit']}/about/rules", link, subject, body])
    print(f"Wrote {len(queue)} prefilled modmail links to {out}.\n"
          f"Open each link, read the subreddit rules first, edit if needed, press Send, then set that row's "
          f"status to 'Messaged' in subreddits.csv (send at most {config.DAILY_SEND_CAP}/day).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="actually send (default is a dry run)")
    ap.add_argument("--only", default="", help="comma-separated subreddit names to restrict to")
    ap.add_argument("--manual", action="store_true", help="write prefilled modmail links instead of sending")
    args = ap.parse_args()
    if args.manual:
        return write_manual(read_subs(), args.only)

    rows = read_subs()
    only = {s.strip().lower() for s in args.only.split(",") if s.strip()}
    queue = [r for r in rows
             if r["rules_flag"] != "FORBID" and r["status"] == "New"
             and float(r["score"]) >= config.MIN_SCORE_TO_CONTACT
             and (not only or r["subreddit"].lower() in only)]
    queue.sort(key=lambda r: -float(r["score"]))

    budget = config.DAILY_SEND_CAP - (sent_today() if args.send else 0)
    if budget <= 0:
        raise SystemExit(f"Daily cap of {config.DAILY_SEND_CAP} already reached - try again tomorrow.")
    batch = queue[:budget]
    print(f"{len(queue)} eligible subreddits; {'sending' if args.send else 'DRY RUN for'} {len(batch)} today.\n")

    reddit = get_reddit(need_login=True) if args.send else None
    for i, row in enumerate(batch):
        subject, body = build_message(row)
        print(f"--- r/{row['subreddit']} (score {row['score']}, {row['rules_flag']}) ---\nSubject: {subject}\n{body}")
        if not args.send:
            continue
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        try:
            reddit.subreddit(row["subreddit"]).message(subject=subject, message=body)
            row["status"] = "Messaged"
            row["notes"] = (row.get("notes", "") + f" | messaged {now[:10]}").strip(" |")
            log({"date_utc": now, "subreddit": row["subreddit"], "subject": subject, "status": "Sent", "error": ""})
            print("  -> sent")
        except Exception as e:
            log({"date_utc": now, "subreddit": row["subreddit"], "subject": subject, "status": "Failed", "error": str(e)[:200]})
            print(f"  -> FAILED: {e}")
        write_subs(rows)   # save after every send
        if i < len(batch) - 1:
            wait = random.randint(config.MIN_DELAY_SECONDS, config.MAX_DELAY_SECONDS)
            print(f"  waiting {wait}s before next send...")
            time.sleep(wait)

    if not args.send:
        print("\nDry run only - nothing was sent. Re-run with --send when the messages look right.")


if __name__ == "__main__":
    main()
