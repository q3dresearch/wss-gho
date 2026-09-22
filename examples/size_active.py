"""Row counts for the active indicators, so scope is measured not guessed.

$count=true is one cheap request per indicator. Sizes vary 60x across the
active set, so which 50 you pick matters more than how many.
"""
import csv, json, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
UA="wss-probe (+https://github.com/q3dresearch)"
ASOF=os.environ.get("GHO_ASOF","2026-09-22")
KIND=os.environ.get("GHO_KIND","census")     # census | sample
SRC=Path(__file__).resolve().parents[1]/"data"/f"gho-activity-{KIND}-{ASOF}.csv"
OUT=SRC.parent/f"gho-active-sizes-{ASOF}.csv"

# This host black-holes IPv6 and urllib waits out a full TCP timeout on every
# request before falling back, which is what made the old cost model 136x too
# slow. See map_activity.py.
import socket
_o=socket.getaddrinfo
socket.getaddrinfo=lambda h,p,f=0,t=0,pr=0,fl=0:_o(h,p,socket.AF_INET,t,pr,fl)

rows=[r for r in csv.DictReader(open(SRC,encoding="utf-8"))
      if r.get("status")=="ok" and r.get("days_since") and int(r["days_since"])<365]
print(f"  active indicators to size: {len(rows)}", flush=True)

def size(r):
    c=r["indicator_code"]
    try:
        u=f"https://ghoapi.azureedge.net/api/{c}?$count=true&$top=1"
        n=json.loads(urllib.request.urlopen(
            urllib.request.Request(u,headers={"User-Agent":UA}),timeout=60).read()).get("@odata.count")
    except Exception:
        n=None
    return {**r,"rows":n if n is not None else ""}

done=[]
with ThreadPoolExecutor(max_workers=12) as ex:
    for i,res in enumerate(ex.map(size,rows),1):
        done.append(res)
        if i%100==0: print(f"    {i}/{len(rows)}",flush=True)
with OUT.open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=["indicator_code","indicator_name","last_published","days_since","rows"],extrasaction="ignore")
    w.writeheader(); w.writerows(done)
ok=[int(r["rows"]) for r in done if r["rows"]]
ok.sort()
print(f"\n  sized {len(ok)} of {len(rows)}")
if ok:
    print(f"  median {ok[len(ok)//2]:,}   mean {sum(ok)//len(ok):,}   min {ok[0]:,}   max {ok[-1]:,}")
    for cut in (5000,20000):
        sub=[x for x in ok if x<=cut]
        print(f"  indicators under {cut:,} rows: {len(sub)}  totalling {sum(sub):,} rows")
    print(f"  ALL active: {sum(ok):,} rows")
