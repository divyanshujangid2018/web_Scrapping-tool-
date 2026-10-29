"""Fetch Apify Google Maps results, enrich with emails/socials from websites, score relevance, write CSV."""
import csv, json, os, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse

TOKEN = os.environ["APIFY_TOKEN"]
DATASET = sys.argv[1] if __name__ == "__main__" else None
OUT = sys.argv[2] if len(sys.argv) > 2 else "sf_student_freelancer_communities.csv"

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
BAD_EMAIL = ("example.", "sentry", "wixpress", ".png", ".jpg", ".gif", ".webp", "@2x", "domain.com", "email.com")
SOCIAL = {"linkedin": "linkedin.com/", "instagram": "instagram.com/", "facebook": "facebook.com/", "twitter_x": ("twitter.com/", "x.com/")}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"}

# Relevance to "communities of students / part-time working students / freelancers"
HIGH = ["student", "college", "university", "campus", "freelanc", "youth", "bootcamp", "hackathon", "intern", "gig"]
MED = ["coworking", "co-working", "community", "meetup", "startup", "staffing", "employment", "career", "club", "association"]


def get(url, timeout=12, limit=600_000):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(limit).decode("utf-8", "ignore")


def fetch_items():
    url = f"https://api.apify.com/v2/datasets/{DATASET}/items?clean=true&format=json&token={TOKEN}"
    return json.loads(get(url, 60, None))


def enrich(site):
    out = {"emails": set(), **{k: "" for k in SOCIAL}}
    if not site:
        return out
    pages = [site]
    try:
        html = get(site)
    except Exception:
        return out
    for path in re.findall(r'href=["\']([^"\']*(?:contact|about|team|connect)[^"\']*)["\']', html, re.I)[:3]:
        u = urljoin(site, path)
        if urlparse(u).netloc == urlparse(site).netloc:
            pages.append(u)
    htmls = [html]
    for u in pages[1:]:
        try:
            htmls.append(get(u))
        except Exception:
            pass
    for h in htmls:
        for e in EMAIL_RE.findall(h):
            e = e.lower().strip(".")
            if not any(b in e for b in BAD_EMAIL):
                out["emails"].add(e)
        for k, pat in SOCIAL.items():
            if out[k]:
                continue
            for p in (pat if isinstance(pat, tuple) else (pat,)):
                m = re.search(r'https?://(?:www\.)?' + re.escape(p) + r'[^"\'\s<>?#]+', h)
                if m and "/share" not in m.group(0) and "intent" not in m.group(0):
                    out[k] = m.group(0)
                    break
    return out


def score(it):
    text = " ".join(str(x) for x in [it.get("title"), it.get("categoryName"), " ".join(it.get("categories") or []), it.get("searchString")]).lower()
    if any(w in text for w in HIGH):
        return "High"
    if any(w in text for w in MED):
        return "Medium"
    return "Low"


def main():
    items = fetch_items()
    seen, rows = set(), []
    for it in items:
        key = it.get("placeId") or (it.get("title"), it.get("address"))
        if key in seen or it.get("permanentlyClosed"):
            continue
        seen.add(key)
        rows.append(it)
    print(f"{len(items)} raw -> {len(rows)} unique", file=sys.stderr)

    with ThreadPoolExecutor(16) as ex:
        enr = list(ex.map(lambda it: enrich(it.get("website")), rows))

    fields = ["Relevance", "Company / Community", "Category", "Matched Search", "Website", "Emails", "Phone",
              "LinkedIn", "Instagram", "Facebook", "Twitter/X", "Address", "City", "Rating", "Reviews", "Google Maps URL"]
    order = {"High": 0, "Medium": 1, "Low": 2}
    out = []
    for it, e in zip(rows, enr):
        out.append({
            "Relevance": score(it),
            "Company / Community": it.get("title"),
            "Category": it.get("categoryName"),
            "Matched Search": it.get("searchString"),
            "Website": it.get("website") or "",
            "Emails": "; ".join(sorted(e["emails"])[:5]),
            "Phone": it.get("phone") or "",
            "LinkedIn": e["linkedin"], "Instagram": e["instagram"], "Facebook": e["facebook"], "Twitter/X": e["twitter_x"],
            "Address": it.get("address") or "",
            "City": it.get("city") or "",
            "Rating": it.get("totalScore") or "",
            "Reviews": it.get("reviewsCount") or "",
            "Google Maps URL": it.get("url") or "",
        })
    out.sort(key=lambda r: (order[r["Relevance"]], r["Emails"] == "", r["Company / Community"] or ""))
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    from collections import Counter
    print("relevance:", Counter(r["Relevance"] for r in out), "with email:", sum(bool(r["Emails"]) for r in out),
          "with website:", sum(bool(r["Website"]) for r in out), file=sys.stderr)


if __name__ == "__main__":
    main()
