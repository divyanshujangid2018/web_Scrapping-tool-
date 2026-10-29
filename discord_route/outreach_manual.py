"""Manual outreach sheet for Discord servers - nothing is joined or sent automatically.

For each server (status New, fit_hits >= 1, score >= threshold) it writes the invite link, the
directory page and a personalised message. You join with your own Discord account, read the rules,
find the partnership/contact channel or open a support ticket (or DM a listed community manager if
the rules allow), paste the message, and set status to "Contacted" in servers.csv.

Usage:  python3 discord_route/outreach_manual.py [--min-score 8] [--us-only]
"""
import argparse
import csv
from pathlib import Path

import config

HERE = Path(__file__).parent
SRC, OUT = HERE / "servers.csv", HERE / "outreach_manual.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-score", type=float, default=8.0)
    ap.add_argument("--us-only", action="store_true")
    args = ap.parse_args()
    if not SRC.exists():
        raise SystemExit("servers.csv not found - run discover.py first.")
    with SRC.open() as f:
        rows = [r for r in csv.DictReader(f) if r["status"] == "New" and int(r["fit_hits"]) >= 1
                and float(r["score"]) >= args.min_score and (not args.us_only or r["us_signal"] == "US")]
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "members", "online", "us_signal", "score", "join_link", "directory_page",
                    "where_to_contact", "message"])
        for r in rows:
            w.writerow([r["name"], r["members"], r["online"], r["us_signal"], r["score"],
                        r["invite_link"] or r["directory_page"], r["directory_page"],
                        "After joining: #partnerships / #contact-staff / #support ticket, or DM the community "
                        "manager listed in #rules or #about (only if DMs to staff are allowed)",
                        config.MESSAGE.format(name=r["name"], sender_name=config.SENDER_NAME, company=config.COMPANY)])
    print(f"Wrote {len(rows)} servers to {OUT}. Contact a few per day by hand; mark them 'Contacted' in servers.csv.")


if __name__ == "__main__":
    main()
