"""Combine scraped picks + agent CSVs, strict dedup vs exclusion list and each other, output master-format rows."""
import csv, glob, json, re, difflib
from final_dedup import norm, domain, GENERIC
JUNK = re.compile(r'example|sentry|wixpress|godaddy|domain\.com|email\.com|yourname|test@|sample|\.png|\.jpg|greensock|youragency|mysite', re.I)
ex_n, ex_d = [], set()
for r in csv.DictReader(open('dedup/exclusion_v2.csv')):
    parts = r['vendor'].split('|')
    if 'Community Managers' in r['source'] and len(parts) > 1: parts = parts[1].split(';')
    for p in parts:
        n = norm(re.sub(r'\(.*?\)', '', p))
        if len(n) >= 3 and n not in GENERIC: ex_n.append(n)
    for d in [domain(r['website'])] + [domain(x) for x in re.split(r'[;,\s]+', r['emails']) if x]:
        if d: ex_d.add(d)
ex_set = set(ex_n)
def dup(name, site, emails):
    n = norm(re.sub(r'\(.*?\)', '', name))
    if n in ex_set: return True
    if any(d and d in ex_d for d in [domain(site)] + [domain(e) for e in emails]): return True
    for e in ex_n:
        if len(n) >= 5 and len(e) >= 5 and (difflib.SequenceMatcher(None, n, e).ratio() >= 0.9 or re.search(r'\b' + re.escape(e) + r'\b', n) and len(e) >= 7): return True
    return False
rows = []
for r in json.load(open('raw2/picks.json')):
    em = [x for x in re.split(r'[;,\s]+', r.get('emails') or '') if '@' in x and not JUNK.search(x)]
    rows.append(dict(v=r['name'], city=r['city'], type=r['type'], site=r['website'], poc=r.get('poc', ''), title=r.get('poc_title', ''), em=em,
                     phone=r.get('phone') or '', li=r.get('linkedin') or r.get('poc_li', ''), size=f"{r['followers']} LinkedIn followers" if r['source'] == 'LinkedIn' and r['followers'] else '',
                     why=re.sub(r'\s+', ' ', r['desc'])[:160], src=r['source'] + (f"; HQ {r['hq']}" if r.get('hq') else ''), rel='High' if r['type'].startswith(('Panel', 'AI data', 'Freelance', 'Gig', 'User testing')) else 'Medium'))
for f in sorted(glob.glob('dedup/v2_*.csv')):
    for r in csv.DictReader(open(f)):
        em = [r.get(k, '').strip() for k in ('Email 1', 'Email 2', 'Email 3') if '@' in r.get(k, '')]
        rows.append(dict(v=r['Vendor'], city=r.get('City', ''), type=r.get('Type', ''), site=r.get('Website', ''), poc=r.get('POC Name', ''), title=r.get('POC Title', ''), em=em,
                         phone=r.get('Phone', ''), li=r.get('LinkedIn', ''), size=r.get('Community Size', ''), why=r.get('Why it fits', '')[:200], src=r.get('Source / confidence', '')[:120],
                         rel='High' if not r.get('Type', '').startswith(('Student', 'Expert')) else 'Medium'))
out, seen_n, seen_d, dropped = [], set(), set(), []
for r in rows:
    n, d = norm(re.sub(r'\(.*?\)', '', r['v'])), domain(r['site'])
    if dup(r['v'], r['site'], r['em']) or n in seen_n or (d and d in seen_d): dropped.append(r['v']); continue
    seen_n.add(n); seen_d.add(d) if d else None; out.append(r)
order = ['Panel', 'AI data', 'User testing', 'Freelance', 'Gig', 'Expert', 'Student', 'Consented']
out.sort(key=lambda r: (r['rel'] != 'High', next((i for i, o in enumerate(order) if r['type'].startswith(o)), 9), not r['poc'], not r['em'], r['v'].lower()))
hdr = ["Vendor", "Relevance", "", "Status", "POC Name", "Email 1", "Email 2", "Email 3", "Email 4", "Email 5", "Phone", "Website", "Scaler POC", "Notes"]
res = [hdr]
for r in out:
    em = (r['em'] + [''] * 5)[:5]
    poc = r['poc'] + (f" ({r['title']})" if r['title'] else '')
    notes = ' | '.join(x for x in [f"City: {r['city']}", f"Type: {r['type']}", r['size'] and f"Community: {r['size']}", r['li'] and f"LinkedIn: {r['li']}", r['why'] and f"Why: {r['why']}", r['src'] and f"Source: {r['src']}"] if x)
    row = [r['v'], r['rel'], '', 'Not contacted', poc, *em, r['phone'], r['site'], '', notes]
    res.append([("'" + c) if isinstance(c, str) and c[:1] in '+=-' else c for c in row])
json.dump(res, open('dedup/final_v2.json', 'w'), ensure_ascii=False)
from collections import Counter
print('rows', len(out), 'dropped dup', len(dropped), dropped[:30])
print(Counter(r['type'] for r in out)); print('POC', sum(bool(r['poc']) for r in out), 'email', sum(bool(r['em']) for r in out))
