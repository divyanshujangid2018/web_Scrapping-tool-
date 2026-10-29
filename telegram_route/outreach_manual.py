"""Build a manual outreach sheet from channels.csv - nothing is sent automatically.

For each contactable channel/group (not NO_PROMO, status New, score >= threshold) it writes the
published admin contact, a t.me link to open that contact, and a personalised message to copy.
You send it yourself from your Telegram account (a few per day), then set status to "Messaged".

Usage:  python3 telegram_route/outreach_manual.py [--min-score 8] [--us-only]
"""
import argparse
import csv
from pathlib import Path

import config

HERE = Path(__file__).parent
SRC, OUT = HERE / "channels.csv", HERE / "outreach_manual.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-score", type=float, default=8.0)
    ap.add_argument("--us-only", action="store_true", help="only channels with a US signal")
    args = ap.parse_args()
    if not SRC.exists():
        raise SystemExit("channels.csv not found - run discover.py first.")
    with SRC.open() as f:
        rows = [r for r in csv.DictReader(f)
                if r["promo_flag"] != "NO_PROMO" and r["status"] == "New"
                and float(r["score"]) >= args.min_score and (not args.us_only or r["us_signal"] == "US")]
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["title", "channel_link", "members", "us_signal", "score", "contact_to_message",
                    "contact_link", "emails", "message"])
        for r in rows:
            contact = (r["admin_contacts"].split("; ")[0] if r["admin_contacts"] else "")
            link = f"https://t.me/{contact.lstrip('@')}" if contact else r["link"]
            msg = config.MESSAGE.format(sender_name=config.SENDER_NAME, company=config.COMPANY,
                                        title=r["title"], members_k=max(1, round(int(r["members"]) / 1000)))
            w.writerow([r["title"], r["link"], r["members"], r["us_signal"], r["score"],
                        contact or "(no admin contact published - check pinned post / channel info)",
                        link, r["emails"], msg])
    print(f"Wrote {len(rows)} rows to {OUT}. Send manually, a few per day, then mark them 'Messaged' in channels.csv.")


if __name__ == "__main__":
    main()
