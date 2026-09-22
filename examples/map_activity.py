"""Map which WHO GHO indicators are actually alive.

Screening evidence, not a capture. Three earlier samples disagreed by 15x
because I chose the indicators; this polls the catalogue so the scoping rule
comes from measurement instead of taste.

`$orderby=Date desc` is mandatory. `Date` is stamped per load batch, not per
indicator, so a series can hold rows with different dates. Without the sort the
API returns an arbitrary row -- DEVICES20 answers 2013-06-11 unsorted and
2022-12-12 sorted. A poller using the naive form reports "unchanged" for ever.

COST -- and a correction, 2026-09-22. This file used to say a request cost
~61s cold, that eight in parallel all returned together "which is a server-side
queue", and that a full census was therefore ~6.7 hours. Every one of those
numbers was wrong, and the sampling design rested on them.

The tell was flat latency. Batches of 6, 16 and 32 all finished in ~136s, and
`$select`, `$filter` and `$apply` forms cost the same as `$orderby`. When the
clock does not move as the work moves, the clock is not timing the work. This
host has an IPv6 blackhole: `urllib` resolves AAAA first and waits out a TCP
timeout before falling back, so every measurement was timing that wait. The
parallel batches "returning together" were eight identical timeouts expiring
together, not a queue -- the API was never the bottleneck.

Forcing AF_INET (see `_ipv4_only`) drops a cold request to ~1.0s: 136x. The
census is ~5 minutes at modest concurrency, not 6.7 hours, so there is no
longer any reason to sample. Set GHO_SAMPLE=all.

Rows are written as they arrive and the run resumes from what is already there.
"""
import csv, json, os, random, socket, threading, urllib.error, urllib.request, datetime as dt
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

def _ipv4_only():
    """This host black-holes IPv6: AAAA routes accept the connection and never
    answer, so urllib pays a full TCP timeout on every request before falling
    back. curl falls back fast, which is why curl-based probes never saw it."""
    orig = socket.getaddrinfo
    socket.getaddrinfo = lambda h, p, f=0, t=0, pr=0, fl=0: orig(h, p, socket.AF_INET, t, pr, fl)

UA      = "wss-probe (+https://github.com/q3dresearch)"
API     = "https://ghoapi.azureedge.net/api"
OUT     = Path(__file__).resolve().parents[1] / "data"
ASOF    = dt.date.fromisoformat(os.environ.get("GHO_ASOF", dt.date.today().isoformat()))
NOW     = dt.datetime(ASOF.year, ASOF.month, ASOF.day, tzinfo=dt.timezone.utc)
WORKERS = int(os.environ.get("GHO_WORKERS", "12"))
SAMPLE  = os.environ.get("GHO_SAMPLE", "400")     # a count, or "all" for the census
SEED    = int(os.environ.get("GHO_SEED", "20260907"))

def get(url, timeout=60):
    return json.loads(urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout).read())

def probe(ind):
    code = ind["IndicatorCode"]
    row = {"indicator_code": code, "indicator_name": (ind.get("IndicatorName") or "")[:180]}
    try:
        v = get(f"{API}/{code}?$top=1&$select=Date&$orderby=Date%20desc")["value"]
    except urllib.error.HTTPError as e:
        return {**row, "status": f"http{e.code}"}
    except Exception as e:
        return {**row, "status": type(e).__name__}
    if not v or not v[0].get("Date"):
        return {**row, "status": "empty"}          # catalogued, no rows: not a failure
    d = v[0]["Date"]
    try:
        age = (NOW - dt.datetime.fromisoformat(d)).days
    except Exception:
        return {**row, "status": "baddate"}
    return {**row, "last_published": d[:10], "days_since": age, "status": "ok"}

def main():
    _ipv4_only()
    OUT.mkdir(parents=True, exist_ok=True)
    inds = get(f"{API}/Indicator")["value"]
    census = SAMPLE == "all"
    if census:
        pool = inds
        path = OUT / f"gho-activity-census-{ASOF}.csv"
    else:
        random.seed(SEED)                          # fixed draw, so a resume continues the same sample
        pool = random.sample(inds, min(int(SAMPLE), len(inds)))
        path = OUT / f"gho-activity-sample-{ASOF}.csv"
    done = set()
    if path.exists():                              # resume
        with path.open(encoding="utf-8") as f:
            done = {r["indicator_code"] for r in csv.DictReader(f)}
    todo = [i for i in pool if i["IndicatorCode"] not in done]
    print(f"  catalogue {len(inds):,}   pool {len(pool):,} ({'census' if census else 'sample'})"
          f"   done {len(done):,}   to do {len(todo):,}   workers {WORKERS}   as-of {ASOF}", flush=True)
    cols = ["indicator_code", "indicator_name", "last_published", "days_since", "status"]
    lock, n = threading.Lock(), 0
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        if not done:
            w.writeheader(); f.flush()
        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            for fut in as_completed([ex.submit(probe, i) for i in todo]):
                r = fut.result()
                with lock:
                    w.writerow(r); f.flush(); n += 1
                    if n % 250 == 0:
                        print(f"    {n:,}/{len(todo):,}", flush=True)
    print(f"\n  done: {n:,} written to {path}", flush=True)

if __name__ == "__main__":
    main()
