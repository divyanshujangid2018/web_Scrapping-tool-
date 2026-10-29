# Telegram sourcing route (Telethon)

Finds **public** Telegram channels and groups whose audience fits the program (paid surveys, side
hustles, WFH / remote jobs, freelancers, app testers, students, US-focused money communities),
scores them, and prepares a **manual** outreach sheet for their admins.

## Files
| File | What it does |
|---|---|
| `config.py` | Keywords, US / promo patterns, scoring weights, message template |
| `discover.py` | Searches public channels/groups → members, posts/day, last post, US signal, promo rules, published admin contacts → `channels.csv` |
| `outreach_manual.py` | Builds `outreach_manual.csv`: admin contact, t.me link, personalised message (you send it yourself) |
| `tg_client.py` | Builds the Telethon client from `.env` |
| `.env.example` | Credential template |

## Setup (once)
1. `pip3 install -r telegram_route/requirements.txt`
2. Go to https://my.telegram.org → **API development tools** → create an app → copy **api_id** and **api_hash**.
3. `cp telegram_route/.env.example telegram_route/.env` and fill them in (don't paste them in chat).
4. First run asks for your phone number and the login code Telegram sends you – **type these in the
   terminal yourself** (run it in your own terminal, not through chat). A local `*.session` file is saved;
   treat it like a password.

## Run
```bash
python3 telegram_route/discover.py                       # → telegram_route/channels.csv
python3 telegram_route/outreach_manual.py --us-only      # → telegram_route/outreach_manual.csv
```

## channels.csv columns (portal import)
`title, username, link, type, members, posts_per_day, last_post_utc, active, us_signal, promo_flag,
admin_contacts, emails, links, keyword_hits, score, status, description, last_checked, notes`

- **us_signal** `US` / `Non-US` / `Unknown` (from title + description).
- **promo_flag** `PROMO_OK` (admins accept/sell promos – contact listed), `NO_PROMO` (never contacted), `UNKNOWN`.
- **status** `New` → `Messaged` → `Replied` / `Declined`; `Skip - no promo`. Re-runs keep your statuses.

## Score
`2 × log10(members) + 0.2 × posts/day (cap 30) + 2 if US (−3 if Non-US) + 1.5 if PROMO_OK + 1 if a
contact is published + 0.5 × keyword hits (cap 4)`; halved if no post in 30 days; `NO_PROMO` = 0.

## Rules & limits
- **Public data only.** It reads public channel info and recent post dates. It never exports member lists
  or private users' data, and never sends messages.
- **Manual outreach only.** Telegram bans accounts that cold-DM many people. Message only the admin
  contacts the channel publishes for ads/partnerships, a few per day, from your own account.
- **Rate limits.** The script pauses between requests and obeys Telegram's FloodWait. Don't lower the delays.
- **Terms.** Follow Telegram's Terms of Service and API terms; keep it small-scale and honest
  (US adults 18+, consented, PII redacted, USD 600–800, no passwords requested).
- **Many money/side-hustle channels are scams or non-US.** Check each one before contacting; prefer `US`
  + `PROMO_OK` + active channels.
