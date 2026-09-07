"""Two charts that frame the GHO archive before it exists.

Neither shows a revision -- that needs a second capture. They show why the
capture is scoped the way it is, and state a prediction the archive will test.
"""
import collections, csv, datetime as dt, glob, json, os, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)          # wss-gho/
ROOT = os.path.dirname(os.path.dirname(REPO))
sys.path.insert(0, os.path.join(ROOT, "larder", "tools", "cfr"))  # shared svgkit
from svgkit import *                                          # noqa: E402
OUT = os.path.join(HERE, "charts")
UA = "wss-probe (+https://github.com/q3dresearch)"

# ---------------------------------------------------------------- chart 1
src = os.path.join(REPO, "reference", "indicator-activity-2026-09-07.csv")
rows = [r for r in csv.DictReader(open(src, encoding="utf-8")) if r.get("status") == "ac" or r.get("status") == "ok"]
ages = sorted(int(r["days_since"]) for r in rows if r.get("days_since"))
BUCKETS = [("<1y", 0, 365), ("1–2y", 365, 730), ("2–4y", 730, 1460), (">4y", 1460, 10**9)]
counts = [(lab, sum(1 for a in ages if lo <= a < hi)) for lab, lo, hi in BUCKETS]
n = len(ages)

W, L, R = 1180, 80, 300
PW = W - L - R
T, PH = 150, 250
H = T + PH + 110
b = []
b.append(txt(L, 46, "Most of WHO's indicator catalogue stopped being updated", 21, INK, weight="600"))
b.append(txt(L, 73, f"When each of {n} randomly sampled indicators was last republished. "
                    "Scoping by this alone picks the citable core.", 13.5, MUTE))
bw = PW / len(counts)
mx = max(c for _, c in counts)
for i, (lab, c) in enumerate(counts):
    h = PH * c / mx
    x = L + bw * i + bw * 0.16
    live = lab == "<1y"
    b.append(rect(x, T + PH - h, bw * 0.68, h, ORANGE if live else BLUE, op=0.9 if live else 0.5))
    b.append(txt(x + bw * 0.34, T + PH - h - 10, f"{c}", 15, INK, anchor="middle", weight="600"))
    b.append(txt(x + bw * 0.34, T + PH - h - 28, f"{c/n:.0%}", 11.5,
                 ORANGE if live else MUTE, anchor="middle", weight="600"))
    b.append(txt(x + bw * 0.34, T + PH + 20, lab, 13, INK if live else MUTE,
                 anchor="middle", weight="600" if live else "normal"))
b.append(line(L, T + PH, L + PW, T + PH, MUTE))
nx = L + PW + 26; y0 = T + 4
for ln in wrap("The 14% republished within a year are the indicators anyone cites: "
               "under-five mortality, infant deaths, HIV in pregnancy, immunisation "
               "coverage, air pollution mortality.", 250):
    b.append(txt(nx, y0, ln, 12, ORANGE, weight="600")); y0 += 17
y0 += 14
for ln in wrap("The dormant 59% are policy inventories last touched over four years ago — "
               "\"social costs of alcohol use\", \"supervision requirements for buprenorphine\" "
               "— several stamped 13 years old.", 250):
    b.append(txt(nx, y0, ln, 12, MUTE)); y0 += 17
y0 += 14
for ln in wrap("Capturing only the active set is therefore a mechanical rule, not a "
               "judgement about which indicators deserve to exist.", 250):
    b.append(txt(nx, y0, ln, 12, INK)); y0 += 17
b.append(txt(L, H - 32, f"Source: ghoapi.azureedge.net, {n} of 3,098 indicators drawn at random, "
                        "2026-09-07. Median last republication 4.7 years.", 10.5, MUTE))
open(os.path.join(OUT, "catalogue-activity.svg"), "w").write(doc(W, H, b))

# ---------------------------------------------------------------- chart 2
# Ranking countries by interval width puts microstates on top -- Andorra, San
# Marino, Niue -- where the band is wide because there are very few births, not
# because registration is weak. That is a different mechanism and it would make
# the chart argue something it cannot support. So this shows the two
# DISTRIBUTIONS instead, which is the actual claim, and names examples.
# Read from the archive, not the API. A chart that needs the network cannot
# regenerate the same output later and cannot run in CI at all.
d = []
for f in sorted(glob.glob(os.path.join(REPO, "derived", "observations", "*.csv"))):
    for r in csv.DictReader(open(f, encoding="utf-8")):
        # Both-sexes, all-quintiles only. The archive keeps every breakdown,
        # but a country's headline uncertainty is the aggregate one -- mixing
        # in the sex and quintile splits, each with its own wider band, would
        # measure something else. Dropping this filter moves the reported
        # ratio from 2.3x to 1.7x.
        if (r["entity_id"].startswith("MDG_0000000007:")
                and "SEX_BTSX" in r["entity_id"]
                and "WEALTHQUINTILE_TOTL" in r["entity_id"]):
            d.append(r)
names = {}
with open(os.path.join(REPO, "reference", "country-names-2026-09-07.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f):
        names[r["code"]] = r["title"]
G20 = {"ARG","AUS","BRA","CAN","CHN","FRA","DEU","IND","IDN","ITA","JPN","MEX",
       "RUS","SAU","ZAF","KOR","TUR","GBR","USA"}
# derived stores one row per metric, so value/low/high must be regrouped by
# (entity, reference year) before a band can be computed. That long format is
# what lets a revision surface as a changed row rather than a new one.
cell = collections.defaultdict(dict)
for r in d:
    if r["metric"] in ("value", "low", "high"):
        cell[(r["entity_id"], r["observed_at"])][r["metric"]] = r["value"]
per = collections.defaultdict(list)
for (ent, _yr), m in cell.items():
    if not {"value", "low", "high"} <= set(m):
        continue
    try:
        v, lo, hi = float(m["value"]), float(m["low"]), float(m["high"])
    except ValueError:
        continue
    if v:
        per[ent.split(":")[1]].append((hi - lo) / v)
# Countries only. Regional and income-group aggregates carry tighter bands
# because more data sits behind them, and counting them as "everyone else"
# understates the gap (4.3x instead of 4.8x).
country = {k: st.median(v) for k, v in per.items() if len(v) >= 3 and k in names}
g = sorted((v, k) for k, v in country.items() if k in G20)
ng = sorted((v, k) for k, v in country.items() if k not in G20)

W2, L2, R2 = 1180, 118, 300
PW2 = W2 - L2 - R2
T2, ROW = 168, 118
H2 = T2 + ROW * 2 + 128
CAP = 1.5                                   # x-axis cap; wider values are pinned
b = []
b.append(txt(L2 - 38, 46, "Half the world's child-mortality figures are estimates with very wide bands",
             21, INK, weight="600"))
b.append(txt(L2 - 38, 73, "Uncertainty on under-five mortality as a share of the estimate, one dot "
                          "per country. A wide band means modelled, not registered.", 13.5, MUTE))
def strip(y, vals, colour, label, sub):
    b.append(txt(L2 - 12, y + 6, label, 13, colour, anchor="end", weight="600"))
    b.append(txt(L2 - 12, y + 23, sub, 10.5, MUTE, anchor="end"))
    b.append(line(L2, y + 40, L2 + PW2, y + 40, GRID))
    for v, code in vals:
        x = L2 + PW2 * min(v, CAP) / CAP
        b.append(circ(x, y + 40, 4, colour, stroke="#ffffff", sw=0.8))
    m = st.median([v for v, _ in vals])
    mx_ = L2 + PW2 * min(m, CAP) / CAP
    b.append(line(mx_, y + 16, mx_, y + 64, INK, 2))
    b.append(txt(mx_, y + 12, f"median ±{m*100:.0f}%", 11.5, INK, anchor="middle", weight="600"))
strip(T2, g, BLUE, "G20", f"{len(g)} countries")
strip(T2 + ROW, ng, ORANGE, "everyone else", f"{len(ng)} countries")
for i in range(0, int(CAP * 100) + 1, 25):
    x = L2 + PW2 * (i / 100) / CAP
    b.append(txt(x, T2 + ROW + 84, f"±{i}%", 11, MUTE, anchor="middle"))
b.append(txt(L2 + PW2, T2 + ROW + 100, f"(dots beyond ±{int(CAP*100)}% are pinned to the edge)",
             10, MUTE, anchor="end"))
ex = [c for _, c in sorted(ng, reverse=True) if c in ("SSD", "MMR", "COG", "PNG", "TCD")][:4]
nx = L2 + PW2 + 26; y0 = T2 + 2
gm, ngm = st.median([v for v, _ in g]), st.median([v for v, _ in ng])
for ln in wrap(f"The two distributions barely overlap. Outside the G20 the median interval is "
               f"{ngm/gm:.1f}x wider -- {ngm*100:.0f}% of the estimate against {gm*100:.0f}%. "
               f"Measured on the rows this repo would capture (country, both sexes, all "
               f"wealth quintiles).", 250):
    b.append(txt(nx, y0, ln, 12, INK)); y0 += 17
y0 += 12
for ln in wrap("The very widest are microstates where few births make any estimate uncertain. "
               "The ones that matter are large and poorly registered: "
               + ", ".join(names.get(c, c) for c in ex) + ".", 250):
    b.append(txt(nx, y0, ln, 11.5, MUTE)); y0 += 16
y0 += 12
for ln in wrap("PREDICTION, before the archive exists: revision magnitude will track interval "
               "width. If so, the countries most written about in development research are the "
               "ones whose history moves most.", 250):
    b.append(txt(nx, y0, ln, 12, ORANGE, weight="600")); y0 += 17
b.append(txt(L2 - 38, H2 - 32, "Source: ghoapi.azureedge.net MDG_0000000007, country rows with "
                               "published uncertainty intervals, 2026-09-07.", 10.5, MUTE))
open(os.path.join(OUT, "uncertainty-and-prediction.svg"), "w").write(doc(W2, H2, b))
print("  wrote catalogue-activity.svg and uncertainty-and-prediction.svg")


# ---------------------------------------------------------------- chart 3
# WHO does not restate continuously. 71% of active indicators share a release
# date with at least one other, so revisions arrive as batches -- which is what
# makes a monthly cadence match the source rather than merely seem reasonable.
sizes = os.path.join(REPO, "reference", "indicator-sizes-2026-09-07.csv")
srows = [r for r in csv.DictReader(open(sizes, encoding="utf-8")) if r.get("last_published")]
by_date = collections.Counter(r["last_published"] for r in srows)
dates = sorted(by_date)
shared = sum(v for v in by_date.values() if v >= 2) / sum(by_date.values())

W3, L3, R3 = 1240, 80, 330
PW3 = W3 - L3 - R3
T3, PH3 = 158, 226
H3 = T3 + PH3 + 110
b = []
b.append(txt(L3, 46, "WHO restates in releases, not continuously", 21, INK, weight="600"))
b.append(txt(L3, 73, f"When each of the {len(srows)} captured indicators was last republished. "
                     f"{shared:.0%} share a date with another indicator.", 13.5, MUTE))
d0 = dt.date.fromisoformat(dates[0]); d1 = dt.date.fromisoformat(dates[-1])
span = max(1, (d1 - d0).days)
mx3 = max(by_date.values())
placed = []                       # (x, y) of labels already drawn
for dte, c in sorted(by_date.items()):
    x = L3 + PW3 * (dt.date.fromisoformat(dte) - d0).days / span
    h = PH3 * c / mx3
    batch = c >= 3
    b.append(rect(x - 5, T3 + PH3 - h, 10, h, ORANGE if batch else BLUE, op=0.9 if batch else 0.55))
    if not batch:
        continue
    # Adjacent release dates sit within a few pixels of each other, so two
    # counts render as one nonsense number ("33"). Lift the label until it
    # clears anything already drawn nearby.
    y = T3 + PH3 - h - 8
    while any(abs(x - px) < 16 and abs(y - py) < 14 for px, py in placed):
        y -= 15
    placed.append((x, y))
    b.append(txt(x, y, str(c), 11.5, ORANGE, anchor="middle", weight="600"))
b.append(line(L3, T3 + PH3, L3 + PW3, T3 + PH3, MUTE))
for m in range(0, span + 1, 61):
    d = d0 + dt.timedelta(days=m)
    x = L3 + PW3 * m / span
    b.append(txt(x, T3 + PH3 + 19, d.strftime("%b %Y"), 11, MUTE, anchor="middle"))
nx = L3 + PW3 + 26; y0 = T3 + 4
for ln in wrap(f"{len(by_date)} distinct release dates across {len(srows)} indicators — "
               f"about two events a month. Orange marks a date carrying three or more.", 246):
    b.append(txt(nx, y0, ln, 12, INK)); y0 += 17
y0 += 13
for ln in wrap("Revisions therefore arrive in batches. A monthly capture sits inside that "
               "rhythm; a daily one would re-fetch the same unchanged series about thirty "
               "times per release.", 246):
    b.append(txt(nx, y0, ln, 12, ORANGE, weight="600")); y0 += 17
y0 += 13
for ln in wrap("Answered from the first capture. It is also the only question here that "
               "needed no second one.", 246):
    b.append(txt(nx, y0, ln, 11.5, MUTE)); y0 += 16
b.append(txt(L3, H3 - 30, "Source: ghoapi.azureedge.net, the Date field of the 48 indicators this "
                          "repo captures, read 2026-09-07.", 10.5, MUTE))
open(os.path.join(HERE, "charts", "restatement-rhythm.svg"), "w").write(doc(W3, H3, b))
print("  wrote restatement-rhythm.svg")


# ---------------------------------------------------------------- chart 4
# "Historical database" is doing a lot of work in how GHO is described. Two
# panels, because the shallowness shows up in two independent ways: almost all
# values describe recent years, and most indicators are not time series at all.
peryear = collections.Counter(); span = collections.defaultdict(set)
for f in sorted(glob.glob(os.path.join(REPO, "derived", "observations", "*.csv"))):
    y = int(os.path.basename(f)[:4])
    for r in csv.DictReader(open(f, encoding="utf-8")):
        if r["metric"] != "value":
            continue
        peryear[y] += 1
        span[r["entity_id"].split(":")[0]].add(y)
dec = collections.Counter()
for y, c in peryear.items():
    dec[y // 10 * 10] += c
tot = sum(dec.values())
buckets = collections.Counter()
for ys in span.values():
    n = max(ys) - min(ys)
    buckets["one year" if n == 0 else "under 10" if n < 10 else "10–30" if n < 30 else "over 30"] += 1

W4, L4, R4 = 1240, 84, 300
PW4 = W4 - L4 - R4
TA, PHA = 156, 190
TB, PHB = TA + PHA + 104, 150
H4 = TB + PHB + 100
b = []
b.append(txt(L4, 46, "GHO reaches back to 1931, and almost none of it is old", 21, INK, weight="600"))
b.append(txt(L4, 73, f"{sum(peryear.values()):,} values across 48 indicators, by the year each one "
                     "describes.", 13.5, MUTE))
b.append(txt(L4, TA - 16, "Values by reference decade", 12.5, INK, weight="600"))
decs = sorted(dec)
bw = PW4 / len(decs)
mx = max(dec.values())
for i, d in enumerate(decs):
    c = dec[d]
    h = PHA * c / mx
    x = L4 + bw * i + bw * 0.16
    thin = c / tot < 0.03
    b.append(rect(x, TA + PHA - h, bw * 0.68, h, ORANGE if thin else BLUE, op=0.9 if thin else 0.6))
    b.append(txt(x + bw * 0.34, TA + PHA - h - 8, f"{c/tot:.0%}" if c/tot >= 0.01 else "<1%",
                 11, ORANGE if thin else INK, anchor="middle", weight="600"))
    b.append(txt(x + bw * 0.34, TA + PHA + 18, f"{d}s", 11, MUTE, anchor="middle"))
b.append(line(L4, TA + PHA, L4 + PW4, TA + PHA, MUTE))
b.append(txt(L4, TB - 16, "How many years each indicator actually spans", 12.5, INK, weight="600"))
order = ["one year", "under 10", "10–30", "over 30"]
bw2 = PW4 / len(order)
mx2 = max(buckets.values())
for i, k in enumerate(order):
    c = buckets[k]
    h = PHB * c / mx2
    x = L4 + bw2 * i + bw2 * 0.16
    lone = k in ("one year", "under 10")
    b.append(rect(x, TB + PHB - h, bw2 * 0.68, h, ORANGE if lone else BLUE, op=0.9 if lone else 0.6))
    b.append(txt(x + bw2 * 0.34, TB + PHB - h - 8, str(c), 14, INK, anchor="middle", weight="600"))
    b.append(txt(x + bw2 * 0.34, TB + PHB + 18, k, 12, INK if lone else MUTE, anchor="middle",
                 weight="600" if lone else "normal"))
b.append(line(L4, TB + PHB, L4 + PW4, TB + PHB, MUTE))
nx = L4 + PW4 + 26; y0 = TA + 2
for ln in wrap("71% of every value describes the year 2000 or later. Everything before 1960 is "
               "1.6% of the archive.", 250):
    b.append(txt(nx, y0, ln, 12, INK)); y0 += 17
y0 += 12
for ln in wrap("Under-five mortality reaches 1931 and infant deaths 1951. They are two series "
               "out of forty-eight, and the deep past is a thin decorative tail rather than the "
               "bulk of the record.", 250):
    b.append(txt(nx, y0, ln, 12, MUTE)); y0 += 17
y0 = TB + 2
for ln in wrap("Only 8 indicators span more than thirty years. Six are a single year and are not "
               "time series at all — air pollution 2021, sexual violence 2023.", 250):
    b.append(txt(nx, y0, ln, 12, ORANGE, weight="600")); y0 += 17
b.append(txt(L4, H4 - 30, "Source: this repository's first capture, 2026-09-07. Values only; "
                          "uncertainty bounds and load stamps excluded.", 10.5, MUTE))
open(os.path.join(HERE, "charts", "history-is-shallow.svg"), "w").write(doc(W4, H4, b))
print("  wrote history-is-shallow.svg")


# ---------------------------------------------------------------- chart 5
# Who is in the record at all. This one is about the world rather than about
# WHO's housekeeping: coverage is drawn along sovereignty lines, and the drop
# is a cliff rather than a gradient.
meta = {}
with open(os.path.join(REPO, "reference", "country-names-2026-09-07.csv"), encoding="utf-8") as f:
    for r in csv.DictReader(f):
        meta[r["code"]] = {"Title": r["title"], "ParentTitle": r["region"]}
ctry_ind = collections.defaultdict(set)
for f in glob.glob(os.path.join(REPO, "derived", "observations", "*.csv")):
    for r in csv.DictReader(open(f, encoding="utf-8")):
        if r["metric"] != "value":
            continue
        p = r["entity_id"].split(":")
        if p[1] in meta:
            ctry_ind[p[1]].add(p[0])
cnt = {c: len(v) for c, v in ctry_ind.items()}
BANDS = [(36, 48, "36–48"), (24, 35, "24–35"), (10, 23, "10–23"), (2, 9, "2–9"), (1, 1, "exactly 1")]
band_n = [(lab, sum(1 for v in cnt.values() if lo <= v <= hi)) for lo, hi, lab in BANDS]
ones = sorted((meta[c]["Title"] for c, v in cnt.items() if v == 1))

W5, L5, R5 = 1300, 150, 372
PW5 = W5 - L5 - R5
T5, ROW5 = 168, 40
H5 = T5 + ROW5 * len(band_n) + 150
b = []
b.append(txt(L5 - 66, 46, "The global health record is drawn along sovereignty lines",
             21, INK, weight="600"))
b.append(txt(L5 - 66, 73, f"How many of the 48 captured indicators cover each of "
                          f"{len(cnt)} places. The median is {sorted(cnt.values())[len(cnt)//2]}.",
             13.5, MUTE))
mx5 = max(v for _, v in band_n)
for i, (lab, v) in enumerate(band_n):
    y = T5 + ROW5 * i
    w = PW5 * v / mx5
    thin = lab in ("exactly 1", "2–9")
    b.append(rect(L5, y, w, ROW5 - 14, ORANGE if thin else BLUE, op=0.9 if thin else 0.55))
    b.append(txt(L5 - 10, y + ROW5 - 24, lab, 12.5, INK if thin else MUTE, anchor="end",
                 weight="600" if thin else "normal"))
    # The longest bar fills the panel, so its count would land in the note
    # column. Put the label inside the bar once it passes three-quarters.
    if w > PW5 * 0.75:
        b.append(txt(L5 + w - 10, y + ROW5 - 24, f"{v} places", 11.5, "#ffffff",
                     anchor="end", weight="600"))
    else:
        b.append(txt(L5 + w + 8, y + ROW5 - 24, f"{v} places", 11.5, INK))
b.append(txt(L5 - 10, T5 - 14, "indicators", 10.5, MUTE, anchor="end"))
# The gap sits between the 10-23 band and 2-9. Put the note above the line and
# far enough right to clear the "16 places" count that follows the short bar.
gapy = T5 + ROW5 * 3 - 7
b.append(line(L5, gapy, L5 + PW5, gapy, INK, 1, dash="4,3"))
b.append(txt(L5 + PW5 * 0.42, gapy - 7,
             "only 3 places sit between — the drop is a cliff, not a gradient",
             11, INK, style="italic"))
nx = L5 + PW5 + 24; y0 = T5 - 4
for ln in wrap("The 18 places covered by exactly one indicator are every one of them a "
               "territory or dependency, not a sovereign state:", 258):
    b.append(txt(nx, y0, ln, 12, INK)); y0 += 16
y0 += 6
for ln in wrap(", ".join(ones), 258):
    b.append(txt(nx, y0, ln, 11, ORANGE, weight="600")); y0 += 15
y0 += 10
for ln in wrap("The single indicator reaching them is basic drinking water — produced by the "
               "WHO/UNICEF Joint Monitoring Programme, which counts places by geography rather "
               "than by statehood.", 258):
    b.append(txt(nx, y0, ln, 11.5, MUTE)); y0 += 16
y0 += 10
for ln in wrap("Réunion has about 870,000 residents and appears in one indicator of "
               "forty-eight.", 258):
    b.append(txt(nx, y0, ln, 11.5, INK, weight="600")); y0 += 16
b.append(txt(L5 - 66, H5 - 30, "Source: this repository's first capture, 2026-09-07. Places as "
                               "listed in the GHO COUNTRY dimension; regional aggregates excluded.",
             10.5, MUTE))
open(os.path.join(HERE, "charts", "who-is-missing.svg"), "w").write(doc(W5, H5, b))
print("  wrote who-is-missing.svg")
