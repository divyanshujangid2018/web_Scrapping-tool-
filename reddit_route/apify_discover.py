"""Step 1 via Apify (no Reddit API key needed) - writes the same subreddits.csv as discover.py.

1. scrapestorm/reddit-communities-search-scraper---cheap: subreddit search per keyword
   (members, online users, description, NSFW) - about $0.003 per subreddit.
2. red_crawler/reddit-subreddits (endpoint "rules"): rules for the top candidates - about $0.002 each,
   flagged FORBID / MODS_FIRST / OK with the same patterns as discover.py.

Uses the Apify key in the project-root .env (Apify_API_KEY). Then run:
    python3 reddit_route/outreach.py --manual   (one-click modmail links you send yourself)

Usage:  python3 reddit_route/apify_discover.py [--per-keyword 20] [--rules-top 60] [--max-usd 1.0]
        python3 reddit_route/apify_discover.py --reuse   # no new search: re-rank the subreddits already in
                                                         # subreddits*.csv and fetch only missing rules
Search costs ~$0.0032 per result, so the search size is capped up front to stay inside --max-usd.
"""
import argparse
import csv
import json
import math
import os
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import config
from discover import FIELDS, rule_flag

HERE = Path(__file__).parent
OUT = HERE / "subreddits.csv"
API = "https://api.apify.com/v2"
SEARCH_ACTOR = "scrapestorm~reddit-communities-search-scraper---cheap"
RULES_ACTOR = "red_crawler~reddit-subreddits"
SEARCH_USD_PER_ITEM = 0.0032
# Keep only subreddits whose name/description is about earning, surveys, gigs, testing or work.
RELEVANT = re.compile(r"money|earn|income|hustle|survey|cash|\bgig|freelanc|wfh|work ?online|work from home|remote|"
                      r"\bjobs?\b|hire|tester|testing|sample|prolific|mturk|swagbucks|qmee|frugal|reward|paid|participant", re.I)
EXCLUDE = re.compile(r"nsfw|porn|onlyfans|gonewild|crypto|bitcoin|nft|forex|trading|gambl|casino|india|nigeria|pakistan", re.I)


def token():
    for line in (HERE.parent / ".env").read_text().splitlines():
        if line.startswith("Apify_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("Apify_API_KEY not found in project-root .env")


def call(method, path, body=None):
    url = f"{API}{path}{'&' if '?' in path else '?'}token={TOKEN}"
    req = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def run_actor(actor, inp):
    """Run synchronously and return dataset items."""
    run = call("POST", f"/acts/{actor}/runs", inp)["data"]
    while run["status"] in ("READY", "RUNNING"):
        time.sleep(5)
        run = call("GET", f"/actor-runs/{run['id']}")["data"]
    items = call("GET", f"/datasets/{run['defaultDatasetId']}/items?clean=true&format=json")
    return items if isinstance(items, list) else [], round(run.get("usageTotalUsd") or 0, 3)


def score(subs, online, flag, hits):
    if flag == "FORBID":
        return 0.0
    s = config.WEIGHT_SUBSCRIBERS * math.log10(max(subs, 1))
    s += 2.0 * min(online / max(subs, 1) * 100, 2)          # online share (activity proxy), capped
    s += config.BONUS_MODS_FIRST if flag == "MODS_FIRST" else (config.BONUS_NO_FLAG if flag == "OK" else 0)
    s += config.BONUS_KEYWORD_HITS * min(hits, 4)
    return round(s, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-keyword", type=int, default=20)
    ap.add_argument("--rules-top", type=int, default=30)
    ap.add_argument("--max-usd", type=float, default=1.0)
    ap.add_argument("--reuse", action="store_true", help="skip the paid search; use subreddits already in the CSVs")
    args = ap.parse_args()
    spent = 0.0

    known = {}                                   # rows from earlier runs: reuse their rules flags
    for path in sorted(HERE.glob("subreddits*.csv")):
        with path.open() as f:
            for r in csv.DictReader(f):
                k = r["subreddit"].lower()
                if r["rules_flag"] == "FORBID" and not any(re.search(p, m, re.I) for m in r["flagged_rules"].split("; ")
                                                           for p in config.FORBID_PATTERNS):
                    r = {**r, "rules_flag": "UNCHECKED", "flagged_rules": ""}   # flagged by older, stricter patterns
                prev = known.get(k)
                if prev is None or (prev["rules_flag"] == "UNCHECKED" and r["rules_flag"] != "UNCHECKED"):
                    known[k] = {**r, "subscribers": max(int(r["subscribers"] or 0), int((prev or {}).get("subscribers") or 0))}
                else:
                    prev["subscribers"] = max(int(r["subscribers"] or 0), int(prev["subscribers"] or 0))

    items = []
    if not args.reuse:
        maxitems = min(args.per_keyword * len(config.SEARCH_KEYWORDS), int(args.max_usd * 0.7 / SEARCH_USD_PER_ITEM))
        items, cost = run_actor(SEARCH_ACTOR, {"keywords": config.SEARCH_KEYWORDS, "maxitems": maxitems,
                                               "sort": "relevance", "time": "year"})
        spent += cost
        print(f"search: {len(items)} results (cap {maxitems}), ${cost}")

    subs = {}
    for k, r in known.items():
        online = re.search(r"online now: (\d+)", r.get("notes", ""))
        subs[k] = {"name": r["subreddit"], "members": int(r["subscribers"] or 0),
                   "online": int(online.group(1)) if online else 0, "desc": r.get("title", "")}
    for it in items:
        name = (it.get("display_name") or "").replace("r/", "").strip()
        ctx = it.get("tracking_context") or "{}"
        try:
            nsfw = json.loads(ctx).get("subreddit", {}).get("nsfw", False)
        except json.JSONDecodeError:
            nsfw = False
        members = int(it.get("members") or 0)
        if not name or nsfw or members < config.MIN_SUBSCRIBERS or EXCLUDE.search(f"{name} {it.get('description', '')}"):
            continue
        subs[name.lower()] = {"name": name, "members": members, "online": int(it.get("online") or 0),
                              "desc": (it.get("description") or "").replace("\n", " ")[:300]}
    seeds = {x.lower() for x in config.SEED_SUBREDDITS}
    subs = {k: s for k, s in subs.items()
            if (k in seeds or RELEVANT.search(f"{s['name']} {s['desc']}")) and not EXCLUDE.search(f"{s['name']} {s['desc']}")}
    for seed in config.SEED_SUBREDDITS:          # seeds may not appear in search: look up size/description
        if seed.lower() in subs or seed.lower() in known or args.reuse or spent >= args.max_usd:
            continue
        try:
            info, cost = run_actor(RULES_ACTOR, {"endpoint": "subreddit_info", "info_subreddit": seed})
            spent += cost
            d = info[0] if info else {}
            if d.get("over18") or (d.get("subscribers") or 0) < config.MIN_SUBSCRIBERS:
                continue
            subs[seed.lower()] = {"name": d.get("display_name") or seed, "members": int(d.get("subscribers") or 0),
                                  "online": int(d.get("active_user_count") or d.get("accounts_active") or 0),
                                  "desc": (d.get("public_description") or "").replace("\n", " ")}
        except Exception as e:
            print(f"  info r/{seed} failed: {e}")
    print(f"{len(subs)} candidate subreddits after filters")

    def kw_hits(s):
        blob = f"{s['name']} {s['desc']}".lower()
        return sum(1 for k in config.SEARCH_KEYWORDS if k in blob)

    ranked = sorted(subs.values(), key=lambda s: -(math.log10(max(s["members"], 1)) + 0.5 * kw_hits(s)))
    rules = {}
    have_flag = {k for k, r in known.items() if r["rules_flag"] not in ("UNCHECKED", "")}
    for s in [x for x in ranked if x["name"].lower() not in have_flag][: args.rules_top]:
        if spent >= args.max_usd:
            print("budget reached - remaining subreddits get rules_flag UNCHECKED")
            break
        try:
            res, cost = run_actor(RULES_ACTOR, {"endpoint": "subreddit_rules", "rules_subreddit": s["name"]})
            spent += cost
            rule_list = res[0].get("rules") if (res and "rules" in res[0]) else res   # one item per rule
            rules[s["name"].lower()] = [{"name": x.get("short_name", ""), "description": x.get("description", "")}
                                        for x in (rule_list or [])]
        except Exception as e:
            print(f"  rules r/{s['name']} failed: {e}")
    print(f"rules fetched for {len(rules)} subreddits; total spent ${round(spent, 3)}")

    existing = known
    rows = []
    for key, s in subs.items():
        if key in rules:
            flag, matched = rule_flag(rules[key])
        elif key in have_flag:
            flag, matched = known[key]["rules_flag"], [m for m in known[key]["flagged_rules"].split("; ") if m]
        else:
            flag, matched = "UNCHECKED", []
        hits = kw_hits(s)
        prev = existing.get(key, {})
        rows.append({
            "subreddit": s["name"], "url": f"https://www.reddit.com/r/{s['name']}/", "subscribers": s["members"],
            "posts_per_day": "", "rules_flag": flag, "flagged_rules": "; ".join(matched), "mod_usernames": "",
            "score": score(s["members"], s["online"], flag, hits) if flag != "UNCHECKED" else 0.0,
            "status": prev.get("status") or ("Skip - rules forbid" if flag == "FORBID" else "New"),
            "title": s["desc"], "keyword_hits": hits, "nsfw": False,
            "last_checked": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "notes": prev.get("notes") or f"online now: {s['online']}",
        })
    rows.sort(key=lambda r: -float(r["score"]))
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} subreddits to {OUT}. Apify spend ≈ ${round(spent, 3)}")


if __name__ == "__main__":
    TOKEN = token()
    main()
