"""Merge hand-picked LinkedIn/X companies into the SF list, drop non-profits, prioritise freelance communities."""
import csv, glob, json, re
from concurrent.futures import ThreadPoolExecutor
from build_list import enrich

CSV = "sf_student_freelancer_communities.csv"
FREELANCE = "Freelance community / marketplace"
GIG = "Gig-work platform"
STAFF = "Staffing / part-time jobs"
STUDENT = "Student community / university"
CREATOR = "Creator / remote-work community"

PICKS = {  # LinkedIn name -> (segment, relevance)
    "Arc.dev": (FREELANCE, "High"), "Fiverr": (FREELANCE, "High"), "Folio": (FREELANCE, "High"),
    "hireahuman.quest": (FREELANCE, "High"), "HYI.AI": (FREELANCE, "High"), "AppExert": (FREELANCE, "High"),
    "Olibr – Free Job Community Platform": (FREELANCE, "High"), "CloudPeeps": (FREELANCE, "High"), "YOSS": (FREELANCE, "High"),
    "Cad Crowd - hire 3D modeling, CAD services an": (FREELANCE, "High"), "Make Writing Your Job": (FREELANCE, "High"),
    "Freelance Recruiters Worldwide": (FREELANCE, "High"), "FractionL": (FREELANCE, "High"), "TalentCheetah Inc.": (FREELANCE, "High"),
    "Speedlancer Inc": (FREELANCE, "High"), "gigexchange": (FREELANCE, "High"), "Wigiwork Inc": (FREELANCE, "High"),
    "MarketersClique": (FREELANCE, "High"), "Plural.com": (FREELANCE, "High"), "OnContracting": (FREELANCE, "High"),
    "Copywriter Central": (FREELANCE, "High"), "eventsGIG": (FREELANCE, "High"), "Freelance BIM": (FREELANCE, "High"),
    "Workers On Call": (FREELANCE, "High"), "GetIncredibles": (FREELANCE, "High"), "Croovs": (FREELANCE, "High"),
    "Get Gigs Inc": (FREELANCE, "High"), "Our Work Hub": (FREELANCE, "High"), "One Fine Hire": (FREELANCE, "High"),
    "Freelancer Gang": (FREELANCE, "High"), "Viedit moviemakers network": (FREELANCE, "High"), "Soulo": (FREELANCE, "High"),
    "Human Cloud": (FREELANCE, "High"), "Branded.me": (FREELANCE, "High"), "Techworkers": (FREELANCE, "High"),
    "Freelancehub.cloud": (FREELANCE, "High"), "TechZen": (FREELANCE, "High"), "SetCollab": (FREELANCE, "High"),
    "Uptima Entrepreneur Cooperative": (FREELANCE, "Medium"), "Self-Employed": (FREELANCE, "High"),
    "FoKola Fiverr Freelancers & Services🎗": (FREELANCE, "Medium"), "Matchbox - The startup talent network": (FREELANCE, "Medium"),
    "Talent Connect Network": (FREELANCE, "Medium"), "Alto Logica": (FREELANCE, "Medium"), "EmpowerX": (FREELANCE, "Medium"),
    "TaskHuman": (GIG, "High"), "Lugg": (GIG, "High"), "Stride": (GIG, "High"), "Everlance": (GIG, "High"), "Teller": (GIG, "High"),
    "HyreCar": (GIG, "High"), "Para - For Drivers": (GIG, "High"), "SNAPSHYFT® Labor Marketplace": (GIG, "High"),
    "Giggi": (GIG, "Medium"), "CoDo": (GIG, "Medium"), "ErrandIt": (GIG, "Medium"), "Thor Technologies": (GIG, "Medium"),
    "Courial": (GIG, "Medium"), "Directly": (GIG, "High"), "GreenLight.ai": (GIG, "Medium"), "Nomad Rides": (GIG, "Medium"),
    "EMERGING BLUE": (STAFF, "High"), "Artisan Creative": (STAFF, "High"), "Work Sandy": (STAFF, "High"),
    "The Job Shop": (STAFF, "Medium"), "Recruit N Refer Technology Inc.": (STAFF, "Medium"), "ForceBrands": (STAFF, "Medium"),
    "Fuzia| Fuzia Talent - On-Demand Growth & Exec": (STAFF, "Medium"), "Remote Workers Co.": (STAFF, "High"),
    "Developer Students": (STUDENT, "High"), "Course Hero": (STUDENT, "High"), "Student PreMed Advising Network": (STUDENT, "Medium"),
    "San José State University": (STUDENT, "Medium"), "De Anza College": (STUDENT, "Medium"),
    "Foothill-De Anza Community College District": (STUDENT, "Medium"), "West Valley College": (STUDENT, "Medium"),
    "San Jose City College": (STUDENT, "Medium"), "Mission College": (STUDENT, "Medium"), "Evergreen Valley College": (STUDENT, "Medium"),
    "Student Media at UCSC": (STUDENT, "Medium"), "Student Living at Stanford": (STUDENT, "Medium"),
    "Bay Area Creator Economy": (CREATOR, "High"), "Content Creator Community": (CREATOR, "High"), "Creator Wizard": (CREATOR, "Medium"),
    "Five O'Clock Club": (CREATOR, "Medium"), "CreatorIQ": (CREATOR, "Medium"), "Oooh": (CREATOR, "Medium"),
}
X_PICKS = {"citronworksinc": (FREELANCE, "Medium"), "freelancefi": (FREELANCE, "Low")}
NONPROFIT = re.compile(r"non-profit|nonprofit|social services|community center|volunteer|youth|housing association|religious", re.I)


def main():
    old = list(csv.DictReader(open(CSV)))
    kept, dropped = [], 0
    for r in old:
        if NONPROFIT.search(r["Category"]) and "student" not in r["Company / Community"].lower():
            dropped += 1
            continue
        r.setdefault("Source", "Google Maps")
        if "cowork" in r["Category"].lower():
            r["Segment"] = "Freelancer / coworking / startup"
        kept.append(r)

    li = {}
    for f in glob.glob("raw/li_*.json"):
        for c in json.load(open(f)):
            li.setdefault(c["name"][:45], c)
    known = {r["Company / Community"].lower() for r in kept}
    new = []
    for name, (seg, rel) in PICKS.items():
        c = li.get(name)
        if not c or c["name"].lower() in known:
            continue
        loc = next((l for l in c.get("locations") or [] if l.get("city")), {}) or {}
        new.append({"Relevance": rel, "Segment": seg, "Company / Community": c["name"],
                    "Category": (c.get("industries") or [{}])[0].get("name", ""),
                    "Matched Search": "LinkedIn", "Website": c.get("website") or "", "Phone": c.get("phone") or "",
                    "LinkedIn": c.get("linkedinUrl") or "", "Address": ", ".join(x for x in [loc.get("line1"), loc.get("city"), loc.get("geographicArea")] if x),
                    "City": loc.get("city") or "San Francisco", "Source": "LinkedIn",
                    "LinkedIn Followers": c.get("followerCount") or "", "Employees": c.get("employeeCount") or "",
                    "Description": re.sub(r"\s+", " ", c.get("description") or "")[:300]})
    for u in json.load(open("raw/x_all.json")):
        if u["username"] in X_PICKS:
            seg, rel = X_PICKS[u["username"]]
            site = next((e.get("expanded_url") for e in (u.get("profile_bio") or {}).get("entities", {}).get("url", {}).get("urls", [])), "") or ""
            new.append({"Relevance": rel, "Segment": seg, "Company / Community": u["name"], "Category": "X profile",
                        "Matched Search": "X", "Website": site, "Twitter/X": f"https://x.com/{u['username']}",
                        "City": u.get("location") or "", "Source": "X (Twitter)", "LinkedIn Followers": "",
                        "Description": (u.get("description") or "")[:300]})

    with ThreadPoolExecutor(16) as ex:
        enr = list(ex.map(lambda r: enrich(r["Website"]), new))
    for r, e in zip(new, enr):
        r["Emails"] = "; ".join(sorted(e["emails"])[:5])
        for k, col in [("linkedin", "LinkedIn"), ("instagram", "Instagram"), ("facebook", "Facebook"), ("twitter_x", "Twitter/X")]:
            r[col] = r.get(col) or e[k]

    rows = kept + new
    seg_order = {FREELANCE: 0, "Freelancer / coworking / startup": 1, GIG: 2, CREATOR: 3, STAFF: 4,
                 "Staffing / part-time jobs": 4, STUDENT: 5, "Bootcamp / training": 6, "Platform / tech company": 7}
    rel_order = {"High": 0, "Medium": 1, "Low": 2}
    rows.sort(key=lambda r: (rel_order[r["Relevance"]], seg_order.get(r["Segment"], 9), r.get("Emails", "") == "", r["Company / Community"]))
    fields = ["Relevance", "Segment", "Company / Community", "Category", "Source", "Description", "Website", "Emails", "Phone",
              "LinkedIn", "Twitter/X", "Instagram", "Facebook", "LinkedIn Followers", "Employees", "Address", "City",
              "Rating", "Reviews", "Matched Search", "Google Maps URL"]
    with open(CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(f"dropped non-profits: {dropped}; kept {len(kept)}; added {len(new)}; total {len(rows)}")
    print(Counter(r["Segment"] for r in rows).most_common())
    print(Counter(r["Relevance"] for r in rows), "new with email:", sum(bool(r["Emails"]) for r in new))


if __name__ == "__main__":
    main()
