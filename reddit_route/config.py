"""Settings for the Reddit sourcing route. Edit freely; no secrets live here (see .env)."""

# Keywords used to search for subreddits (Reddit's subreddit search).
SEARCH_KEYWORDS = [
    "paid surveys", "side hustle", "work from home", "get paid for apps", "beta testers",
    "data privacy", "quantified self", "make money online", "gig work", "paid research studies",
    "user testing", "focus groups", "college students jobs", "freelance", "remote work",
]

# Seed subreddits to always check (named from memory - the script verifies they exist and are active).
SEED_SUBREDDITS = [
    "beermoney", "WorkOnline", "sidehustle", "signupsforpay", "WFHJobs", "SampleSize",
    "beermoneyglobal", "slavelabour", "forhire", "QuantifiedSelf", "privacy", "UserTesting",
    "TestMyApp", "betatests", "povertyfinance", "studentsph", "college", "gigwork",
]

MAX_RESULTS_PER_KEYWORD = 25      # subreddits returned per keyword search
MIN_SUBSCRIBERS = 5_000           # ignore tiny subreddits
ACTIVITY_SAMPLE = 100             # newest posts sampled to estimate posts/day
SKIP_NSFW = True

# Rule text patterns. FORBID = skip the subreddit. MODS_FIRST = allowed only via modmail (good for us).
FORBID_PATTERNS = [
    r"no (self[- ]?)?promotion", r"no advertis", r"no solicit", r"no recruit", r"no referral",
    r"no surveys?", r"no (paid )?offers?", r"no job (posts|offers)", r"no marketing",
    r"no commercial", r"no affiliate", r"don'?t (promote|advertise|solicit)",
]
MODS_FIRST_PATTERNS = [
    r"(message|contact|ask) (the )?mod", r"mod approval", r"approved by (the )?mod",
    r"modmail (us|the mods) (first|before)", r"with (mod )?permission", r"pre-?approv",
]

# Scoring weights (higher score = contact first). Subreddits with a FORBID flag are never contacted.
WEIGHT_SUBSCRIBERS = 2.0          # x log10(subscribers)
WEIGHT_POSTS_PER_DAY = 0.15       # x posts/day (capped)
POSTS_PER_DAY_CAP = 50
BONUS_MODS_FIRST = 2.0
BONUS_NO_FLAG = 1.0
BONUS_KEYWORD_HITS = 0.5          # x number of our keywords found in name/description (capped at 4)

# Outreach safety limits (Reddit shadow-bans accounts that send many near-identical messages).
DAILY_SEND_CAP = 5                # max modmails per run/day
MIN_DELAY_SECONDS = 180           # random delay between sends (3-8 minutes)
MAX_DELAY_SECONDS = 480
MIN_SCORE_TO_CONTACT = 8.0

# Message template. {subreddit}, {subscribers_k}, {rule_note} and {sender_name} are filled per subreddit.
SENDER_NAME = "Divyanshu"
COMPANY = "Scaler AI Labs"
SUBJECT = "Partnership request for r/{subreddit} - paid data-contribution study (US members)"
MESSAGE = """Hi r/{subreddit} mod team,

I'm {sender_name} from {company}. I'm reaching out to you first rather than posting, because I want to respect r/{subreddit}'s rules{rule_note}.

We're running a consented, paid research program for US adults (aged 18 and over): participants download their own data exports from 6-8 everyday apps (Gmail/Outlook plus apps like Google Drive, LinkedIn, YouTube or DoorDash) and upload them on our platform, where all personal information is redacted. Approved contributors are paid USD 600-800 each. No passwords or account access are ever requested.

Given r/{subreddit}'s community of ~{subscribers_k}k members, would you be open to either (a) us making one clearly-labelled post following whatever format you prefer, or (b) you sharing it yourselves? Happy to send full details, answer questions, or adjust anything to fit your rules - and completely understand if it's not a fit.

Thanks for your time,
{sender_name}
{company}
"""
