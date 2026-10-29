"""Find and score Discord servers for the sourcing program.

1. Searches the public directory discordservers.com for each term in config.SEARCH_TERMS and reads the
   server list it publishes (name, description, server id).
2. Opens each server's directory page for member count, NSFW flag and invite code.
3. Verifies live numbers with Discord's public invite endpoint (no login): approximate members,
   online members, description, features (COMMUNITY / PARTNERED / VERIFIED).
4. Filters off-topic/risky servers (crypto, gambling, NSFW, gaming...), scores the rest, writes servers.csv.

No Discord account is used and nothing is joined or messaged.
Usage:  python3 discord_route/discover.py            # full run
        python3 discord_route/discover.py --pages 1  # quick test
"""
import argparse
import csv
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import config

HERE = Path(__file__).parent
OUT = HERE / "servers.csv"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
FIELDS = ["name", "server_id", "invite_link", "directory_page", "members", "online", "online_ratio",
          "us_signal", "fit_hits", "features", "nsfw", "score", "status", "description", "found_via",
          "last_checked", "notes"]


def get(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def search_page(term, page):
    url = f"https://discordservers.com/search/{urllib.parse.quote(term)}" + (f"?page={page}" if page > 1 else "")
    html = get(url).replace('\\"', '"')
    m = re.search(r'"@type":"ItemList".*?"itemListElement":(\[.*?\])\}', html)
    if not m:
        return []
    try:
        items = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    out = []
    for it in items:
        sid = re.search(r"/server/(\d+)", it.get("url", ""))
        if sid:
            out.append({"server_id": sid.group(1), "name": it.get("name", ""), "description": it.get("description", "")})
    return out


def server_page(sid):
    html = get(f"https://discordservers.com/server/{sid}").replace('\\"', '"')
    def grab(key, pat=r'"?([^",}]*)"?'):
        m = re.search(rf'"{key}":{pat}', html)
        return m.group(1) if m else ""
    return {"invite": grab("customInvite", r'"([^"]+)"'), "members": grab("members", r"(\d+)"),
            "nsfw": grab("nsfw", r"(true|false)")}


def invite_info(code):
    try:
        d = json.loads(get(f"https://discord.com/api/v10/invites/{urllib.parse.quote(code)}?with_counts=true"))
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError):
        return {}
    g = d.get("guild") or {}
    return {"members": d.get("approximate_member_count"), "online": d.get("approximate_presence_count"),
            "description": g.get("description") or "", "features": g.get("features") or [], "name": g.get("name")}


def matches(patterns, text):
    return [p for p in patterns if re.search(p, text, re.I)]


def score(members, ratio, fit, us, features):
    s = config.W_MEMBERS * math.log10(max(members, 1)) + config.W_ONLINE_RATIO * min(ratio, 1)
    s += config.W_FIT_HITS * min(fit, 4)
    s += config.BONUS_US if us == "US" else (-config.PENALTY_NON_US if us == "Non-US" else 0)
    s += config.BONUS_COMMUNITY if "COMMUNITY" in features else 0
    s += config.BONUS_PARTNERED_VERIFIED if ({"PARTNERED", "VERIFIED"} & set(features)) else 0
    return round(s, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=config.MAX_PAGES_PER_TERM)
    args = ap.parse_args()

    existing = {}
    if OUT.exists():
        with OUT.open() as f:
            existing = {r["server_id"]: r for r in csv.DictReader(f)}

    found = {}
    for term in config.SEARCH_TERMS:
        for page in range(1, args.pages + 1):
            try:
                items = search_page(term, page)
            except Exception as e:
                print(f"search '{term}' p{page} failed: {e}")
                break
            if not items:
                break
            for it in items:
                found.setdefault(it["server_id"], {**it, "found_via": term})
            time.sleep(config.REQUEST_DELAY)
    print(f"{len(found)} servers listed")

    rows, skipped = [], 0
    for sid, it in found.items():
        text = f"{it['name']} {it['description']}"
        if matches(config.EXCLUDE_PATTERNS, text):
            skipped += 1
            continue
        try:
            sp = server_page(sid)
            time.sleep(config.REQUEST_DELAY)
        except Exception:
            sp = {"invite": "", "members": "", "nsfw": ""}
        if sp.get("nsfw") == "true":
            skipped += 1
            continue
        live = invite_info(sp["invite"]) if sp.get("invite") else {}
        if sp.get("invite"):
            time.sleep(config.INVITE_DELAY)
        members = int(live.get("members") or sp.get("members") or 0)
        if members < config.MIN_MEMBERS:
            continue
        online = int(live.get("online") or 0)
        desc = (live.get("description") or it["description"] or "").replace("\n", " ")
        full = f"{it['name']} {desc}"
        if matches(config.EXCLUDE_PATTERNS, full):
            skipped += 1
            continue
        fit = len(matches(config.FIT_PATTERNS, full))
        if config.REQUIRE_FIT and fit == 0:
            skipped += 1
            continue
        us = "US" if matches(config.US_PATTERNS, full) else ("Non-US" if matches(config.NON_US_PATTERNS, full) else "Unknown")
        feats = live.get("features", [])
        ratio = round(online / members, 3) if members and online else 0
        prev = existing.get(sid, {})
        rows.append({
            "name": live.get("name") or it["name"], "server_id": sid,
            "invite_link": f"https://discord.gg/{sp['invite']}" if sp.get("invite") else "",
            "directory_page": f"https://discordservers.com/server/{sid}",
            "members": members, "online": online, "online_ratio": ratio, "us_signal": us, "fit_hits": fit,
            "features": "; ".join(f for f in feats if f in ("COMMUNITY", "PARTNERED", "VERIFIED", "DISCOVERABLE")),
            "nsfw": sp.get("nsfw", ""), "score": score(members, ratio, fit, us, feats),
            "status": prev.get("status") or "New", "description": desc[:400], "found_via": it["found_via"],
            "last_checked": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "notes": prev.get("notes", ""),
        })
        print(f"  {rows[-1]['name'][:40]}: {members:,} members, {online:,} online, {us}, fit {fit}")

    rows.sort(key=lambda r: -float(r["score"]))
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {len(rows)} servers to {OUT} ({skipped} skipped as off-topic/NSFW/risky)")


if __name__ == "__main__":
    main()
