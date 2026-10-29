"""Merge Apify results (raw2/), drop anything in the exclusion list, score fit vs the master's vendor archetypes."""
import csv, glob, json, re, sys
from final_dedup import norm, domain, GENERIC

CITY = {"la": "Los Angeles", "dublin": "Dublin", "dc": "Washington DC", "vegas": "Las Vegas", "miami": "Miami",
        "slc": "Salt Lake City", "houston": "Houston", "dallas": "Dallas", "austin": "Austin", "atlanta": "Atlanta",
        "seattle": "Seattle", "boston": "Boston", "phoenix": "Phoenix", "denver": "Denver", "philly": "Philadelphia",
        "sandiego": "San Diego", "us": "US (multi-city)", "minneapolis": "Minneapolis", "charlotte": "Charlotte", "orlando": "Orlando", "tampa": "Tampa", "nashville": "Nashville", "portland": "Portland", "sanjose": "San Jose", "columbus": "Columbus / Dublin OH", "kc": "Kansas City", "stl": "St. Louis", "cator": "Toronto", "camtl": "Montreal", "cavan": "Vancouver", "ca": "Canada", "detroit": "Detroit", "raleigh": "Raleigh"}

# archetypes of Live / in-talks vendors in the master's Relevant Vendors tab
ARCH = [
    ("Panel / participant recruitment", r"\bpanel(s|ists)?\b|respondent|participant|recruit(ing|ment)? (for|of) (research|studies|participants)|paid (studies|research|focus)|focus group|field ?work|field service|sample provider|online sample|survey (taker|community|app)|mystery shop"),
    ("AI data / crowd workforce", r"data annotation|annotat|labeling|labelling|ai training data|training data|data collection|crowd ?(sourc|work)|human (data|feedback)|rlhf|transcription"),
    ("User testing community", r"user testing|usability|beta test|ux research|crowdtest|testers"),
    ("Expert network", r"expert network|subject matter experts|expert calls|network of (experts|advisors|professionals)"),
    ("Freelance / talent network", r"freelanc|talent network|talent marketplace|independent (professionals|contractors)|vetted (talent|experts|developers)|remote talent"),
    ("Gig / on-demand workforce", r"\bgig\b|on-demand (staff|work)|hourly workers|shift"),
    ("Student / youth community", r"\bstudents?\b|campus|college|gen ?z|youth"),
]
NEG = r"real estate|law firm|attorney|insurance|bank|wealth|investment|lending|mortgage|architecture|construction|restaurant|dental|clinic|hospital|church|school district"


def load_excl():
    names, doms = set(), set()
    for r in csv.DictReader(open("dedup/exclusion_v2.csv")):
        parts = r["vendor"].split("|")
        if "Community Managers" in r["source"] and len(parts) > 1:
            parts = parts[1].split(";")
        for p in parts:
            n = norm(re.sub(r"\(.*?\)", "", p))
            if len(n) >= 3 and n not in GENERIC:
                names.add(n)
        for d in [domain(r["website"])] + [domain(x) for x in re.split(r"[;,\s]+", r["emails"]) if x]:
            if d:
                doms.add(d)
    return names, doms


def rows():
    for f in glob.glob("raw2/li_*.json"):
        key = f.split("li_")[1].split("_")[0]
        for c in json.load(open(f)):
            locs = c.get("locations") or []
            hq = next((l for l in locs if l.get("headquarter")), locs[0] if locs else {}) or {}
            us = any((l.get("country") == "US") for l in locs)
            yield {"name": c.get("name", ""), "website": c.get("website") or "", "linkedin": c.get("linkedinUrl", ""),
                   "desc": re.sub(r"\s+", " ", (c.get("description") or "") + " " + " ".join(c.get("specialities") or [])),
                   "industry": (c.get("industries") or [{}])[0].get("name", ""), "followers": c.get("followerCount") or 0,
                   "employees": c.get("employeeCount") or 0, "phone": c.get("phone") or "",
                   "hq": ", ".join(x for x in [hq.get("city"), hq.get("geographicArea"), hq.get("country")] if x),
                   "us_office": us, "city": CITY.get(key, key), "source": "LinkedIn", "emails": "", "facebook": "", "x": ""}
    for f in glob.glob("raw2/fb_*.json"):
        key = f.split("fb_")[1][:-5]
        for p in json.load(open(f)):
            em = p.get("email") or p.get("emails") or ""
            yield {"name": p.get("pageName") or p.get("title") or "", "website": p.get("website") or "", "linkedin": "",
                   "desc": " ".join(str(p.get(k) or "") for k in ("categories", "category", "intro", "about", "description")),
                   "industry": str(p.get("category") or p.get("categories") or ""), "followers": p.get("followers") or p.get("likes") or 0,
                   "employees": 0, "phone": p.get("phone") or "", "hq": p.get("address") or "", "us_office": True,
                   "city": CITY.get(key, key), "source": "Facebook", "emails": em if isinstance(em, str) else "; ".join(em),
                   "facebook": p.get("pageUrl") or p.get("url") or "", "x": ""}
    for f in glob.glob("raw2/x_*.json"):
        for u in json.load(open(f)):
            site = next((e.get("expanded_url") for e in (u.get("profile_bio") or {}).get("entities", {}).get("url", {}).get("urls", [])), "") or ""
            yield {"name": u.get("name", ""), "website": site, "linkedin": "", "desc": u.get("description") or "",
                   "industry": "X profile", "followers": u.get("followers") or 0, "employees": 0, "phone": "",
                   "hq": u.get("location") or "", "us_office": bool(re.search(r"\b(US|USA|United States|[A-Z]{2})\b|New York|California|Texas|Florida", u.get("location") or "")),
                   "city": u.get("location") or "", "source": "X (Twitter)", "emails": "", "facebook": "", "x": f"https://x.com/{u.get('username')}"}


def main():
    names, doms = load_excl()
    seen, out, excluded = {}, [], []
    for r in rows():
        if not r["name"]:
            continue
        n, d = norm(re.sub(r"\(.*?\)", "", r["name"])), domain(r["website"])
        if n in names or (d and d in doms) or any(domain(e) in doms for e in re.split(r"[;,\s]+", r["emails"]) if e):
            excluded.append(r["name"]); continue
        k = d or n
        if k in seen:
            if r["source"] not in seen[k]["source"]:
                seen[k]["source"] += " + " + r["source"]
            continue
        text = f"{r['name']} {r['industry']} {r['desc']}".lower()
        types = [a for a, pat in ARCH if re.search(pat, text)]
        r["type"] = "; ".join(types)
        r["score"] = len(types) * 2 + (1 if r["us_office"] else -3) + (1 if str(r["followers"]).replace(",","").isdigit() and int(str(r["followers"]).replace(",","")) > 1000 else 0) - (3 if re.search(NEG, text) else 0)
        seen[k] = r
        out.append(r)
    out.sort(key=lambda r: -r["score"])
    json.dump(out, open("raw2/candidates.json", "w"))
    print("candidates", len(out), "excluded as already known", len(excluded))
    print("with >=1 archetype", sum(bool(r["type"]) for r in out))


if __name__ == "__main__":
    main()
