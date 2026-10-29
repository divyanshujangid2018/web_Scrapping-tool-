"""Settings for the Telegram sourcing route. No secrets here (see .env)."""

# Keywords used with Telegram's public search (contacts.Search finds public channels/groups by name/username).
SEARCH_KEYWORDS = [
    "paid surveys", "surveys usa", "side hustle", "side hustle usa", "make money online usa",
    "work from home", "remote jobs usa", "online jobs usa", "gig work", "freelance jobs",
    "freelancers usa", "beta testers", "app testers", "user testing", "focus groups",
    "paid research", "college students usa", "student jobs", "passive income", "beermoney",
    "data privacy", "quantified self", "earn money apps", "mystery shopper",
]

# Optional: public channel/group usernames you already know (without @) - verified by the script.
SEED_USERNAMES = []

SEARCH_LIMIT_PER_KEYWORD = 30   # results requested per keyword
MIN_MEMBERS = 1_000             # ignore tiny channels/groups
ACTIVITY_SAMPLE = 50            # newest messages sampled to estimate posts/day
SLEEP_BETWEEN_CALLS = 2.0       # seconds; keep low request rates to avoid FloodWait

# US-audience signals in title/description (the program needs US adults 18+).
US_PATTERNS = [r"\busa?\b", r"\bu\.s\.", r"united states", r"\bamerica", r"\bus only\b",
               r"\$\d", r"\bdollars?\b", r"new york|california|texas|florida|chicago|los angeles"]
NON_US_PATTERNS = [r"\bindia\b|\bnigeria\b|\bpakistan\b|\bkenya\b|\bphilippines\b|\bbangladesh\b",
                   r"₹|rupee|naira|\bpkr\b|\bngn\b"]

# Description rules. PROMO_OK = admins sell or accept promotions (good: a way in). NO_PROMO = skip.
PROMO_OK_PATTERNS = [r"\bads?\b.*@", r"promo(tion)?s?\b.*@", r"advertis\w*.*@", r"for (ads|promotion|collab|business)",
                     r"collab", r"partnership", r"business enquir", r"contact (us|admin|@)"]
NO_PROMO_PATTERNS = [r"no (ads|advertis|promotion|promo|spam|selling)", r"don'?t (dm|pm) (the )?admin"]

# Scoring (higher = contact first). NO_PROMO channels score 0 and are never suggested.
W_MEMBERS = 2.0                 # x log10(members)
W_POSTS_PER_DAY = 0.2           # x posts/day (capped)
POSTS_PER_DAY_CAP = 30
BONUS_US = 2.0
PENALTY_NON_US = 3.0
BONUS_PROMO_OK = 1.5
BONUS_HAS_CONTACT = 1.0
BONUS_KEYWORD_HITS = 0.5        # x keyword hits (capped at 4)
DEAD_DAYS = 30                  # last post older than this -> marked inactive (score halved)

# Manual outreach message (you send it yourself to the listed admin contact).
SENDER_NAME = "Divyanshu"
COMPANY = "Scaler AI Labs"
MESSAGE = """Hi! I'm {sender_name} from {company}. I found {title} ({members_k}k members) and wanted to ask the admin team first, rather than posting.

We run a consented, paid research program for US adults (18+): people download their own data exports from 6-8 everyday apps (Gmail/Outlook plus apps like Google Drive, LinkedIn, YouTube or DoorDash) and upload them on our platform, where personal information is redacted. Approved contributors are paid USD 600-800 each. No passwords or account access are ever requested.

Would you be open to a paid promotion or partnership to share this with your US members? Happy to send full details and follow your rules."""
