"""Settings for the Discord sourcing route. No secrets needed."""

# Search terms on the public directory discordservers.com (/search/<term>).
SEARCH_TERMS = [
    "surveys", "paid surveys", "side hustle", "make money", "beermoney", "rewards", "get paid",
    "work from home", "remote work", "freelance", "freelancers", "gig work", "jobs",
    "user testing", "beta testing", "testers", "focus groups", "research", "students", "college",
    "university", "cashback", "passive income", "online jobs", "usa",
]
MAX_PAGES_PER_TERM = 3          # each page lists ~16-24 servers
MIN_MEMBERS = 500
REQUEST_DELAY = 1.5             # seconds between directory requests (be polite)
INVITE_DELAY = 1.0              # seconds between Discord invite lookups

# Skip servers whose name/description match these (off-topic, risky or not our audience).
EXCLUDE_PATTERNS = [
    r"crypto|bitcoin|\bbtc\b|\beth\b|nft|web3|token|airdrop|forex|trading|trader|signals|prop firm|stocks? alert",
    r"casino|gambl|betting|\bbet\b|slots",
    r"nsfw|18\+ only|porn|onlyfans|\bnudes?\b|e-?girl|dating|hookup|erp\b",
    r"roleplay|\brp\b server|anime|hentai|minecraft|fortnite|roblox|valorant|gta|gaming community",
    r"hack|cheat|leak|crack|carding|cvv|method|refund service|account (shop|sale)",
    r"politic|maga|trump|democrat|republican|war\b|military|tactical|conservative|liberal",
    r"homework|assignment|essay writing|exam help|do your|tutoring service",
    r"religio|church|islam|bible|anime|kpop|furry|meme",
]
REQUIRE_FIT = True              # keep only servers matching at least one FIT_PATTERN
# Relevance keywords (name/description) - our audience.
FIT_PATTERNS = [
    r"survey", r"side ?hustle", r"make money|earn money|earning", r"beer ?money", r"reward", r"paid",
    r"work from home|wfh|remote", r"freelanc", r"\bgig", r"\bjobs?\b|career|intern", r"user ?test|beta ?test|tester",
    r"focus group|research stud|participant", r"student|college|university|campus", r"cash ?back|cashback",
]
US_PATTERNS = [r"\busa?\b|\bu\.s\.|united states|america|\bus[- ]only", r"\$\d|dollar",
               r"new york|california|texas|florida|chicago|los angeles|boston|seattle"]
NON_US_PATTERNS = [r"india|indian|nigeria|pakistan|philippines|bangladesh|kenya|indonesia|brasil|brazil|türk|deutsch",
                   r"₹|rupee|naira|\bpkr\b|\bngn\b|\binr\b"]

# Scoring
W_MEMBERS = 2.0                 # x log10(members)
W_ONLINE_RATIO = 4.0            # x online/members (active community)
W_FIT_HITS = 1.0                # x fit pattern hits (capped at 4)
BONUS_US = 2.0
PENALTY_NON_US = 3.0
BONUS_COMMUNITY = 0.5           # Discord "COMMUNITY" feature (has rules/announcement setup)
BONUS_PARTNERED_VERIFIED = 1.0

# Manual outreach message (post in their partnership/contact channel or open a support ticket).
SENDER_NAME = "Divyanshu"
COMPANY = "Scaler AI Labs"
MESSAGE = """Hi {name} team! I'm {sender_name} from {company}. I'm reaching out to the staff first rather than posting, to respect your rules.

We run a consented, paid research program for US adults (18+): participants download their own data exports from 6-8 everyday apps (Gmail/Outlook plus apps like Google Drive, LinkedIn, YouTube or DoorDash) and upload them on our platform, where personal information is redacted. Approved contributors are paid USD 600-800 each. No passwords or account access are ever requested.

Would your community be open to a partnership or a sponsored announcement for US members? Happy to share full details, follow your format, or compensate the server. Who is the best person to talk to?"""
