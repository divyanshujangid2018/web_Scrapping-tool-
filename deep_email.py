"""Deep crawl company sites for emails: common contact/about/team/privacy paths + Cloudflare-protected emails."""
import json, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse
UA={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
EM=re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
JUNK=re.compile(r"example|sentry|wixpress|godaddy|domain\.com|email\.com|yourname|yourcompany|test@|sample|\.png|\.jpg|\.webp|\.gif|greensock|mysite|brand\.com|@2x|u00|noreply|no-reply",re.I)
PATHS=["","/contact","/contact-us","/contactus","/about","/about-us","/team","/our-team","/leadership","/privacy","/privacy-policy","/terms","/careers","/partners","/participate","/join"]
def get(u):
    try:
        with urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=10) as r: return r.read(800000).decode("utf-8","ignore")
    except Exception: return ""
def cf(h):
    out=[]
    for enc in re.findall(r'data-cfemail="([0-9a-f]+)"',h)+re.findall(r'/cdn-cgi/l/email-protection#([0-9a-f]+)',h):
        k=int(enc[:2],16); out.append("".join(chr(int(enc[i:i+2],16)^k) for i in range(2,len(enc),2)))
    return out
def crawl(site):
    if not site: return []
    if not site.startswith("http"): site="https://"+site
    p=urlparse(site); base=f"{p.scheme}://{p.netloc}"; dom=p.netloc.replace("www.","")
    found=[]
    for path in PATHS:
        h=get(base+path) if path else get(site)
        if not h: continue
        for e in EM.findall(h)+cf(h)+[m.replace("%40","@") for m in re.findall(r'mailto:([^"\'?>\s]+)',h)]:
            e=e.lower().strip(".")
            if "@" in e and not JUNK.search(e) and e not in found: found.append(e)
        if len(found)>=4: break
    # prefer same-domain emails
    root=dom.split(".")[-2] if dom.count(".")>=1 else dom
    found.sort(key=lambda e:(root not in e.split("@")[1], e.split("@")[0] in ("privacy","legal","dpo","abuse")))
    return found[:4]
if __name__=="__main__":
    rows=json.load(open(sys.argv[1]))
    with ThreadPoolExecutor(16) as ex: res=list(ex.map(lambda r: crawl(r["site"]), rows))
    for r,e in zip(rows,res): r["found"]=e
    json.dump(rows,open(sys.argv[2],"w"))
    print("found for",sum(bool(r["found"]) for r in rows),"of",len(rows))
