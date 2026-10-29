# Reddit sourcing route

Finds subreddits whose members fit the program (paid surveys, side hustles, WFH, app testers,
privacy / quantified-self communities), scores them, and contacts their moderators by modmail,
slowly and politely. Outputs a CSV your portal can import.

## Files
| File | What it does |
|---|---|
| `config.py` | Keywords, seed subreddits, rule patterns, scoring weights, send limits, message template |
| `discover.py` | Step 1 – search, collect subscribers / posts-per-day / rules / mods, score → `subreddits.csv` |
| `outreach.py` | Step 2 – modmail the top subreddits. **Dry run by default**; `--send` to really send |
| `inbox_watch.py` | Reads replies, marks `Replied - review` / `Declined`, stops follow-up → `replies.csv` |
| `reddit_client.py` | Builds the Reddit client from `.env` |
| `.env.example` | Template for credentials (copy to `.env`) |

## Setup (once)
1. `pip3 install -r reddit_route/requirements.txt`
2. Create a free **script** app at https://www.reddit.com/prefs/apps (redirect URI: `http://localhost:8080`).
3. `cp reddit_route/.env.example reddit_route/.env` and fill in the client ID/secret (and, for sending,
   the username/password of an **established** Reddit account). Don't paste these into chat.

## Run
```bash
python3 reddit_route/discover.py            # → reddit_route/subreddits.csv
python3 reddit_route/outreach.py            # dry run: review every message first
python3 reddit_route/outreach.py --send     # sends up to DAILY_SEND_CAP (default 5) with 3-8 min gaps
python3 reddit_route/inbox_watch.py         # check replies (or --loop 30 to check every 30 min)
```

## subreddits.csv columns (portal import)
`subreddit, url, subscribers, posts_per_day, rules_flag, flagged_rules, mod_usernames, score, status,
title, keyword_hits, nsfw, last_checked, notes`

- **rules_flag**: `FORBID` (rules ban promotion/solicitation → never contacted), `MODS_FIRST`
  (rules say ask mods first → good, scored up), `OK` (no relevant rule found).
- **status**: `New` → `Messaged` → `Replied - review` / `Declined`; `Skip - rules forbid`.
  Re-running `discover.py` keeps existing statuses, so nobody is messaged twice.

## Score
`2 × log10(subscribers) + 0.15 × posts/day (cap 50) + 2 if MODS_FIRST (1 if OK) + 0.5 × keyword hits (cap 4)`;
`FORBID` = 0. Only subreddits with score ≥ 8 are contacted (tune in `config.py`).

## Limits & rules (read before sending)
- **Subreddit rules decide.** Anything flagged `FORBID` is skipped automatically; still skim the rules of
  each subreddit before `--send` – the keyword check can miss nuance.
- **Spam detection.** Reddit shadow-bans accounts that send many near-identical messages. Keep the daily
  cap low (≤5), keep the delays, edit the template, and use an account with real history.
- **API terms.** Reddit's Data API restricts commercial use. Check the current terms before running
  this at any volume, and treat it as small, personal outreach.
- **No emails.** Reddit users are anonymous – outreach is modmail only; there are no addresses to collect.
- The message must stay honest: US adults 18+, consented, data exports with PII redaction, USD 600–800,
  no passwords or account access.
