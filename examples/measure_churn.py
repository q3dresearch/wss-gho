"""How much of GHO's byte-level movement is actually data.

Evidence for `dedupe_canon: json`. Refetches every page this repo has already
captured and sorts the result three ways: bytes identical, data identical but
bytes not, and data changed. Without the middle category the registry cannot
justify treating a changed sha as unchanged, and with it the case is
arithmetic -- storing the middle category costs ~97 MB a month at 442 sources
and preserves nothing.
"""
import csv, glob, gzip, hashlib, json, socket, urllib.request, pathlib, collections, datetime as dt
from concurrent.futures import ThreadPoolExecutor

_o = socket.getaddrinfo   # this host black-holes IPv6; see map_activity.py
socket.getaddrinfo = lambda h, p, f=0, t=0, pr=0, fl=0: _o(h, p, socket.AF_INET, t, pr, fl)

ROOT = pathlib.Path(__file__).resolve().parents[1]
UA = "wss-probe (+https://github.com/q3dresearch)"
TODAY = dt.date.today().isoformat()


def canon(b):
    """Row values with key order and the surrogate Id removed."""
    v = json.loads(b)["value"]
    return hashlib.sha256(json.dumps(
        [{k: r[k] for k in sorted(r) if k != "Id"} for r in v],
        sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def main():
    rows = []
    for p in glob.glob(str(ROOT / "manifest/**/*.csv"), recursive=True):
        rows += list(csv.DictReader(open(p, encoding="utf-8")))
    rows = [r for r in rows if r.get("raw_ref")]
    print(f"  pages captured previously: {len(rows)}", flush=True)

    def one(r):
        old = gzip.decompress((ROOT / r["raw_ref"]).read_bytes())
        try:
            new = urllib.request.urlopen(urllib.request.Request(
                r["url"], headers={"User-Agent": UA}), timeout=180).read()
        except Exception as e:
            return {**r, "verdict": "error", "detail": type(e).__name__}
        if old == new:
            return {**r, "verdict": "bytes_identical", "detail": ""}
        same = canon(old) == canon(new)
        return {**r, "verdict": "data_identical" if same else "data_changed",
                "detail": f"{len(old)}->{len(new)}"}

    out = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        for i, x in enumerate(ex.map(one, rows), 1):
            out.append(x)
            if i % 150 == 0:
                print(f"    {i}/{len(rows)}", flush=True)

    dest = ROOT / "reference" / f"serialisation-churn-{TODAY}.csv"
    with dest.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source_id", "url", "fetched_at",
                                          "content_sha256", "verdict", "detail"],
                           extrasaction="ignore")
        w.writeheader(); w.writerows(out)
    c = collections.Counter(x["verdict"] for x in out)
    print(f"\n  {dict(c)}")
    moved = c["data_identical"] + c["data_changed"]
    print(f"  pages whose BYTES changed: {moved}/{len(out)} ({moved/len(out)*100:.1f}%)")
    print(f"  pages whose DATA  changed: {c['data_changed']}/{len(out)} ({c['data_changed']/len(out)*100:.1f}%)")
    ch = sorted({x["source_id"] for x in out if x["verdict"] == "data_changed"})
    print(f"  indicators with a real revision: {len(ch)} -> {ch}")
    print(f"  written to {dest}")


if __name__ == "__main__":
    main()
