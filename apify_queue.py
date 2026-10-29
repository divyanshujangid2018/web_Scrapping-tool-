"""Run a list of Apify actor jobs with max 5 concurrent runs; save each dataset to raw2/<name>.json."""
import json, os, sys, time, urllib.request

T = os.environ["Apify_API_KEY"]
API = "https://api.apify.com/v2"


def call(method, path, body=None):
    req = urllib.request.Request(f"{API}{path}{'&' if '?' in path else '?'}token={T}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}")


def main(jobs_file, maxc=5):
    jobs = json.load(open(jobs_file))
    pending = [j for j in jobs if not os.path.exists(f"raw2/{j['name']}.json")]
    running = {}
    while pending or running:
        while pending and len(running) < maxc:
            j = pending[0]
            r = call("POST", f"/acts/{j['actor']}/runs", j["input"])
            if "data" not in r:
                if "concurrent" in json.dumps(r):
                    break
                print("FAIL", j["name"], r, flush=True); pending.pop(0); continue
            running[r["data"]["id"]] = pending.pop(0)
        time.sleep(10)
        for rid, j in list(running.items()):
            d = call("GET", f"/actor-runs/{rid}")["data"]
            if d["status"] in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
                items = call("GET", f"/datasets/{d['defaultDatasetId']}/items?clean=true&format=json")
                json.dump(items if isinstance(items, list) else [], open(f"raw2/{j['name']}.json", "w"))
                print(j["name"], d["status"], len(items) if isinstance(items, list) else 0, "items", round(d.get("usageTotalUsd") or 0, 3), "USD", flush=True)
                del running[rid]


if __name__ == "__main__":
    main(sys.argv[1])
