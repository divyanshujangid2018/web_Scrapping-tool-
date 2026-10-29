"""Combine SF + NYC/LA/Chicago leads, drop anything already in the MSL Vendor Master or the US Vendor Leads sheet,
and write the final list in the 'Relevant Vendors' column format."""
import csv, re, sys
from urllib.parse import urlparse

D = "dedup/"
PERSONAL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com", "aol.com", "protonmail.com", "live.com", "me.com", "domain.com", "example.com"}
GENERIC = {"freelance", "freelancer", "self employed", "self", "independent", "student", "consultant", "none", "n a", "na",
           "university", "college", "community", "personal", "unemployed", "contractor", "creator", "remote"}
GENERIC_WORDS = {"freelance", "freelancer", "student", "students", "independent", "creative", "creator", "remote",
                 "talent", "career", "global", "digital", "united", "american", "national", "community", "network"}
SEG_MAP = {"Student community company": "Student community / university", "Staffing (part-time / freelance / student)": "Staffing / part-time jobs",
           "Gig / side-hustle / panel platform": "Gig-work platform"}
SUFFIX = re.compile(r"\b(inc|llc|ltd|co|corp|corporation|company|group|the|hq|official|us|usa|\.com|\.io|\.ai|\.co)\b")


def domain(s):
    s = (s or "").strip().lower()
    if not s:
        return ""
    if "@" in s and "/" not in s:
        s = s.split("@")[-1]
    if "://" not in s:
        s = "http://" + s
    host = urlparse(s).netloc.split(":")[0]
    host = re.sub(r"^www\d?\.", "", host)
    parts = host.split(".")
    if len(parts) > 2 and parts[-2] not in ("co", "com"):
        host = ".".join(parts[-2:])
    return "" if host in PERSONAL or "linkedin" in host or "google" in host else host


def norm(name):
    n = (name or "").lower().split("|")[0]
    n = re.sub(r"\(.*?\)", " ", n)
    n = SUFFIX.sub(" ", n)
    n = re.sub(r"[^a-z0-9]+", " ", n)
    return " ".join(n.split())


def load_existing():
    names, doms = {}, {}
    for r in csv.DictReader(open(D + "master_keys.csv")):
        src = f"MSL Vendor Master / {r['tab'].strip()}"
        parts = r["vendor"].split("|")
        if r["tab"].strip() == "Community Managers" and len(parts) > 1:
            parts = parts[1].split(";")  # org only, not the person's name
        for part in parts:
            n = norm(part)
            if len(n) >= 3 and n not in GENERIC:
                names.setdefault(n, src)
        for d in [domain(r["website"])] + [domain(x) for x in r["email_domains"].split(";")]:
            if d:
                doms.setdefault(d, src)
    for r in csv.DictReader(open(D + "leads_1787075559.csv")):
        src = "US MultiApp Vendor Leads"
        n = norm(r.get("Company"))
        if len(n) >= 3:
            names.setdefault(n, src)
        for d in [domain(r.get("Website"))] + [domain(x) for x in re.split(r"[;,\s]+", (r.get("POC Email") or "") + " " + (r.get("Support / General Email") or ""))]:
            if d:
                doms.setdefault(d, src)
    return names, doms


def dup_of(name, site, emails, names, doms):
    n = norm(name)
    if n in names:
        return names[n]
    for d in [domain(site)] + [domain(e) for e in emails]:
        if d and d in doms:
            return doms[d]
    # brand-prefix match, e.g. "WeWork Office Space & Coworking" vs "WeWork"
    first = n.split(" ")[0] if n else ""
    if len(first) >= 5 and first not in GENERIC_WORDS and first in names:
        return names[first]
    return None


def sf_pocs():
    try:
        return {r["Vendor"]: r for r in csv.DictReader(open(D + "sf_pocs.csv"))}
    except FileNotFoundError:
        return {}


def sf_rows():
    pocs = sf_pocs()
    for r in csv.DictReader(open("sf_student_freelancer_communities.csv")):
        emails = [e.strip() for e in r["Emails"].split(";") if e.strip()]
        p = pocs.get(r["Company / Community"], {})
        if p.get("Verdict", "").startswith("Drop"):
            continue
        for e in (p.get("Other Email", ""), p.get("POC Email", "")):
            for x in re.split(r"[;,\s]+", e):
                if x and x.lower() not in [y.lower() for y in emails]:
                    emails.insert(0, x)
        r["_poc"], r["_title"] = p.get("POC Name", ""), p.get("POC Title", "")
        r["LinkedIn"] = p.get("POC LinkedIn") or r["LinkedIn"]
        yield {"Vendor": r["Company / Community"], "City": "San Francisco", "Segment": r["Segment"], "Relevance": r["Relevance"],
               "Website": r["Website"], "POC Name": r["_poc"], "POC Title": r["_title"], "Emails": emails, "Phone": r["Phone"],
               "LinkedIn": r["LinkedIn"], "Twitter/X": r["Twitter/X"], "Community Size": r.get("LinkedIn Followers") and f"{r['LinkedIn Followers']} LinkedIn followers" or "",
               "Why": (r["Description"] or r["Category"])[:200], "Source": r["Source"]}


def city_rows(path, city):
    try:
        f = open(path)
    except FileNotFoundError:
        print("missing", path, file=sys.stderr)
        return
    for r in csv.DictReader(f):
        emails = [r.get(k, "").strip() for k in ("Email 1", "Email 2", "Email 3") if r.get(k, "").strip()]
        seg = r.get("Segment", "")
        rel = "High" if seg.startswith(("Freelance", "Gig", "Student")) else "Medium"
        loc = r.get("City", "")
        seg = SEG_MAP.get(seg, seg)
        rel = "High" if seg.startswith(("Freelance", "Gig", "Student")) else "Medium"
        if "expert network" in (r.get("Why it fits", "") + seg).lower():
            rel = "Medium"
        yield {"Vendor": r["Vendor"], "City": city, "Location detail": loc, "Segment": seg, "Relevance": rel, "Website": r.get("Website", ""),
               "POC Name": r.get("POC Name", ""), "POC Title": r.get("POC Title", ""), "Emails": emails, "Phone": r.get("Phone", ""),
               "LinkedIn": r.get("LinkedIn", ""), "Twitter/X": r.get("Twitter/X", ""), "Community Size": r.get("Community Size", ""),
               "Why": r.get("Why it fits", ""), "Source": r.get("Source / confidence", "")}


def main():
    names, doms = load_existing()
    cand = list(sf_rows()) + list(city_rows(D + "new_nyc.csv", "New York")) + list(city_rows(D + "new_la.csv", "Los Angeles")) + list(city_rows(D + "new_chicago.csv", "Chicago"))
    final, removed, seen_n, seen_d = [], [], set(), set()
    for r in cand:
        hit = dup_of(r["Vendor"], r["Website"], r["Emails"], names, doms)
        n, d = norm(r["Vendor"]), domain(r["Website"])
        if hit:
            removed.append((r["Vendor"], r["City"], hit))
            continue
        if n in seen_n or (d and d in seen_d):
            removed.append((r["Vendor"], r["City"], "duplicate within new list"))
            continue
        seen_n.add(n)
        if d:
            seen_d.add(d)
        final.append(r)

    seg_order = ["Freelance", "Gig", "Student", "Creator", "Staffing", "Freelancer / coworking", "Bootcamp", "Platform"]
    final.sort(key=lambda r: ({"High": 0, "Medium": 1, "Low": 2}.get(r["Relevance"], 3),
                              next((i for i, s in enumerate(seg_order) if r["Segment"].startswith(s)), 9),
                              not r["POC Name"], not r["Emails"], r["City"], r["Vendor"]))

    header = ["Vendor", "Relevance", "", "Status", "POC Name", "Email 1", "Email 2", "Email 3", "Email 4", "Email 5",
              "Phone", "Website", "Scaler POC", "Notes"]
    with open("final_vendor_list.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in final:
            em = (r["Emails"] + [""] * 5)[:5]
            poc = r["POC Name"] + (f" ({r['POC Title']})" if r["POC Title"] else "")
            notes = " | ".join(x for x in [
                f"City: {r['City']}" + (f" ({r['Location detail']})" if r.get("Location detail") and r["Location detail"] != r["City"] else ""), f"Segment: {r['Segment']}",
                r["Community Size"] and f"Community: {r['Community Size']}",
                r["LinkedIn"] and f"LinkedIn: {r['LinkedIn']}", r["Twitter/X"] and f"X: {r['Twitter/X']}",
                r["Why"] and f"Why: {r['Why']}", r["Source"] and f"Source: {r['Source']}"] if x)
            w.writerow([r["Vendor"], r["Relevance"], "", "Not contacted", poc, *em, r["Phone"], r["Website"], "", notes])
    with open("dedup/removed_duplicates.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Vendor", "City", "Matched in"])
        w.writerows(removed)
    from collections import Counter
    print("candidates", len(cand), "final", len(final), "removed", len(removed))
    print("by city", Counter(r["City"] for r in final))
    print("by segment", Counter(r["Segment"] for r in final))
    print("removed by source", Counter(x[2] for x in removed))
    print("with POC", sum(bool(r["POC Name"]) for r in final), "with email", sum(bool(r["Emails"]) for r in final))


if __name__ == "__main__":
    main()
