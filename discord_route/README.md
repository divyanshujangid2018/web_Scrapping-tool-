# Discord sourcing route

Finds public Discord servers whose members fit the program (paid surveys, side hustles, rewards,
WFH/remote, freelancers, testers, students), verifies their live size, scores them, and prepares a
**manual** outreach sheet for their staff / community managers. No Discord account, bot or login is used.

## How it works
1. **Directory search** – `discordservers.com/search/<term>` for each term in `config.py` (it publishes a
   machine-readable list of servers per page). Disboard / Discord.me block scripts, so they're not used.
2. **Server page** – member count, NSFW flag and invite code.
3. **Discord invite lookup** – `discord.com/api/v10/invites/<code>?with_counts=true` (public, no login):
   live members, online members, description, features (COMMUNITY / PARTNERED / VERIFIED).
4. **Filter & score** – drops crypto/trading, gambling, NSFW, gaming, hacking/"method" servers; scores the rest.

## Run
```bash
python3 discord_route/discover.py --pages 1      # quick test
python3 discord_route/discover.py                # full run → discord_route/servers.csv
python3 discord_route/outreach_manual.py --us-only   # → discord_route/outreach_manual.csv
```

## servers.csv columns (portal import)
`name, server_id, invite_link, directory_page, members, online, online_ratio, us_signal, fit_hits,
features, nsfw, score, status, description, found_via, last_checked, notes`

## Score
`2 × log10(members) + 4 × online/members + 1 × fit keyword hits (cap 4) + 2 if US (−3 if Non-US)
+ 0.5 if COMMUNITY + 1 if PARTNERED/VERIFIED`.

## Outreach (manual, by design)
Discord's Terms forbid automating a user account ("self-bots") and mass DMs. So:
1. Open the invite link with **your own** account and read the server rules.
2. Look for `#partnerships`, `#contact-staff`, `#support`/ticket, or a named community manager in `#rules`/`#about`.
3. Paste the prepared message there (or DM staff only if the rules allow it). A few servers per day.
4. Set the row's `status` to `Contacted` → `Replied` / `Declined` in `servers.csv`.

## Notes
- Directory data is self-reported by server owners; the invite lookup gives the real live counts.
- Respect the directory's terms and keep request rates low (delays are built in).
- Many "earn money" servers are referral spam – prefer high online ratio, COMMUNITY/PARTNERED, US signal.
