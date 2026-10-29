"""Step 1 - find and score subreddits.

Searches subreddits by keyword (plus seed list), then for each one collects subscribers, posts/day,
rules (flags bans on promotion/solicitation and 'message mods first' rules) and public moderator
usernames. Scores them and writes subreddits.csv (portal-importable).

Usage:  python3 reddit_route/discover.py            # writes reddit_route/subreddits.csv
        python3 reddit_route/discover.py --limit 10  # quick test with fewer results per keyword
"""
import argparse
import csv
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import config
from reddit_client import get_reddit

OUT = Path(__file__).with_name("subreddits.csv")
FIELDS = ["subreddit", "url", "subscribers", "posts_per_day", "rules_flag", "flagged_rules",
          "mod_usernames", "score", "status", "title", "keyword_hits", "nsfw", "last_checked", "notes"]


def rule_flag(rules):
    """Return (flag, matched_rule_names). flag: FORBID > MODS_FIRST > OK."""
    forbid, mods_first = [], []
    for r in rules:
        text = f"{r.get('name', '')} {r.get('description', '')}".lower()
        if any(re.search(p, text) for p in config.FORBID_PATTERNS):
            forbid.append(r.get("name", "")[:60])
        elif any(re.search(p, text) for p in config.MODS_FIRST_PATTERNS):
            mods_first.append(r.get("name", "")[:60])
    if forbid:
        return "FORBID", forbid
    if mods_first:
        return "MODS_FIRST", mods_first
    return "OK", []


def posts_per_day(sub):
    times = [p.created_utc for p in sub.new(limit=config.ACTIVITY_SAMPLE)]
    if len(times) < 2:
        return 0.0
    span_days = max((max(times) - min(times)) / 86400, 1 / 24)
    return round(len(times) / span_days, 1)


def score(subs, ppd, flag, hits):
    if flag == "FORBID":
        return 0.0
    s = config.WEIGHT_SUBSCRIBERS * math.log10(max(subs, 1))
    s += config.WEIGHT_POSTS_PER_DAY * min(ppd, config.POSTS_PER_DAY_CAP)
    s += config.BONUS_MODS_FIRST if flag == "MODS_FIRST" else config.BONUS_NO_FLAG
    s += config.BONUS_KEYWORD_HITS * min(hits, 4)
    return round(s, 2)


def load_existing():
    if not OUT.exists():
        return {}
    with OUT.open() as f:
        return {r["subreddit"].lower(): r for r in csv.DictReader(f)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=config.MAX_RESULTS_PER_KEYWORD)
    args = ap.parse_args()

    reddit = get_reddit()
    existing = load_existing()   # keeps status/notes from earlier runs (no duplicate outreach)

    names = {s.lower(): s for s in config.SEED_SUBREDDITS}
    for kw in config.SEARCH_KEYWORDS:
        try:
            for sub in reddit.subreddits.search(kw, limit=args.limit):
                names.setdefault(sub.display_name.lower(), sub.display_name)
        except Exception as e:
            print(f"search '{kw}' failed: {e}")
        time.sleep(1)
    print(f"{len(names)} candidate subreddits")

    rows = []
    for key, name in sorted(names.items()):
        try:
            sub = reddit.subreddit(name)
            subs = sub.subscribers or 0
            nsfw = bool(sub.over18)
            if subs < config.MIN_SUBSCRIBERS or (config.SKIP_NSFW and nsfw):
                continue
            rules = [{"name": r.short_name, "description": r.description} for r in sub.rules]
            flag, matched = rule_flag(rules)
            try:
                mods = [m.name for m in sub.moderator() if m.name != "AutoModerator"]
            except Exception:
                mods = []   # some subreddits hide their mod list
            ppd = posts_per_day(sub)
            blob = f"{sub.display_name} {sub.title} {sub.public_description}".lower()
            hits = sum(1 for k in config.SEARCH_KEYWORDS if k in blob)
            prev = existing.get(key, {})
            rows.append({
                "subreddit": sub.display_name,
                "url": f"https://www.reddit.com/r/{sub.display_name}/",
                "subscribers": subs,
                "posts_per_day": ppd,
                "rules_flag": flag,
                "flagged_rules": "; ".join(matched),
                "mod_usernames": "; ".join(mods[:10]),
                "score": score(subs, ppd, flag, hits),
                "status": prev.get("status") or ("Skip - rules forbid" if flag == "FORBID" else "New"),
                "title": (sub.title or "")[:120],
                "keyword_hits": hits,
                "nsfw": nsfw,
                "last_checked": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "notes": prev.get("notes", ""),
            })
            print(f"  r/{sub.display_name}: {subs:,} subs, {ppd}/day, {flag}")
        except Exception as e:
            print(f"  r/{name}: skipped ({e.__class__.__name__}: {e})")
        time.sleep(1)   # stay well under Reddit's rate limit

    rows.sort(key=lambda r: -float(r["score"]))
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    ok = sum(1 for r in rows if r["rules_flag"] != "FORBID")
    print(f"\nWrote {len(rows)} subreddits to {OUT} ({ok} contactable, {len(rows) - ok} forbid outreach)")


if __name__ == "__main__":
    main()
