"""Row counts for the active indicators, so scope is measured not guessed.

$count=true is one cheap request per indicator. Sizes vary 60x across the
active set, so which 50 you pick matters more than how many.
"""
import csv, json, os, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
UA="wss-probe (+https://github.com/q3dresearch)"
SRC=Path(__file__).resolve().parents[1]/"data"/"gho-activity-sample-2026-09-07.csv"
OUT=SRC.parent/"gho-active-sizes-2026-09-07.csv"

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
with ThreadPoolExecutor(max_workers=8) as ex:
    for i,res in enumerate(ex.map(size,rows),1):
        done.append(res)
        if i%10==0: print(f"    {i}/{len(rows)}",flush=True)
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
