# web_Scrapping-tool-

Python tools for finding and contacting sourcing partners and online communities: research panels, freelance and gig platforms, and Reddit, Discord and Telegram communities.

## What's in here

| Path | What it does |
|---|---|
| `apify_queue.py` | Runs Apify actors through the REST API (max 5 at once) |
| `build_list.py`, `build_v2.py`, `process_v2.py`, `merge_linkedin_x.py` | Build and merge company lists from scraped sources |
| `deep_email.py` | Crawls company websites for published contact emails |
| `final_dedup.py` | Duplicate check by normalized name and domain |
| `reddit_route/` | Finds subreddits, checks their rules, prepares modmail outreach ([README](reddit_route/README.md)) |
| `discord_route/` | Finds public Discord servers and scores them ([README](discord_route/README.md)) |
| `telegram_route/` | Finds Telegram channels and groups with Telethon ([README](telegram_route/README.md)) |

## Setup

```bash
pip install -r reddit_route/requirements.txt -r telegram_route/requirements.txt
cp .env.example .env                       # Apify key
cp reddit_route/.env.example reddit_route/.env
cp telegram_route/.env.example telegram_route/.env
```

Keys live only in the `.env` files, which are git-ignored. Scraped data and outputs (CSV, XLSX, JSON) are also git-ignored.

## Notes

- Outreach is manual by design: the scripts prepare messages and links; you send them yourself.
- Respect each platform's terms and rate limits. Discord forbids self-bots and mass DMs.
