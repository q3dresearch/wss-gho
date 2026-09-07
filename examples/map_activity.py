"""Map which WHO GHO indicators are actually alive.

Screening evidence, not a capture. Three earlier samples disagreed by 15x
because I chose the indicators; this polls the whole catalogue so the scoping
rule comes from measurement instead of taste.

`$orderby=Date desc` is mandatory. `Date` is stamped per load batch, not per
indicator, so a series can hold rows with different dates. Without the sort the
API returns an arbitrary row -- DEVICES20 answers 2013-06-11 unsorted and
2022-12-12 sorted. A poller using the naive form reports "unchanged" for ever.

COST, measured rather than assumed. The CDN caches popular indicators:
WHOSIS_000001 answers in ~2s, a randomly drawn one in ~15s. Timing the famous
ones and extrapolating gave a 2-hour estimate for what is really ~13 hours
serially. Concurrency helps less than it should -- eight parallel requests all
returned at ~62s together, which is a server-side queue, not latency -- so a
full census is still ~6.7 hours.

A screening decision needs the distribution, not the census: 400 drawn at
random puts the active share inside about +/-4 points, which is enough to say
whether a scoped capture is worth building. Run the census only if it passes.
Rows are written as they arrive and the run resumes from what is already there.
"""
import csv, json, os, sys, threading, urllib.request, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

UA = "wss-probe (+https://github.com/q3dresearch)"
API = "https://ghoapi.azureedge.net/api"
OUT = Path(__file__).resolve().parents[1] / "data"
NOW = dt.datetime(2026, 9, 7, tzinfo=dt.timezone.utc)
WORKERS = 8
SAMPLE = 400          # screening needs a distribution, not a census

def get(url, timeout=45):
    return json.loads(urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout).read())

def probe(ind):
    code = ind["IndicatorCode"]
    try:
        v = get(f"{API}/{code}?$top=1&$orderby=Date%20desc")["value"]
    except Exception as e:
        return {"indicator_code": code, "status": type(e).__name__}
    if not v or not v[0].get("Date"):
        return {"indicator_code": code, "status": "empty"}
    d = v[0]["Date"]
    try:
        age = (NOW - dt.datetime.fromisoformat(d)).days
    except Exception:
        return {"indicator_code": code, "status": "baddate"}
    return {"indicator_code": code,
            "indicator_name": (ind.get("IndicatorName") or "")[:180],
            "last_published": d[:10], "days_since": age, "status": "ok"}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inds = get(f"{API}/Indicator")["value"]
    path = OUT / "gho-activity-sample-2026-09-07.csv"
    done = set()
    if path.exists():                       # resume
        with path.open(encoding="utf-8") as f:
            done = {r["indicator_code"] for r in csv.DictReader(f)}
    import random
    random.seed(20260907)                    # fixed draw, so a resume continues the same sample
    pool = random.sample(inds, min(SAMPLE, len(inds)))
    todo = [i for i in pool if i["IndicatorCode"] not in done]
    print(f"  catalogue {len(inds):,}   random sample {len(pool)}   done {len(done):,}   to do {len(todo):,}", flush=True)
    cols = ["indicator_code", "indicator_name", "last_published", "days_since", "status"]
    lock = threading.Lock()
    n = 0
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        if not done:
            w.writeheader(); f.flush()
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for fut in as_completed([ex.submit(probe, i) for i in todo]):
                r = fut.result()
                with lock:
                    w.writerow(r); f.flush(); n += 1
                    if n % 100 == 0:
                        print(f"    {n:,}/{len(todo):,}", flush=True)
    print(f"\n  done: {n:,} written to {path}", flush=True)

if __name__ == "__main__":
    main()
