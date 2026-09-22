"""Generate one registry entry per active GHO indicator.

The selection rule is unchanged and mechanical: every indicator WHO has
reloaded within the last year, taken from `map_activity.py`'s census. What
changed on 2026-09-22 is only that the census became affordable -- the old
6.7-hour estimate was this host's IPv6 blackhole, not WHO. The 400-indicator
sample it forced put the active share at 14.2% (95% CI 10.9-18.4); the census
says 14.3%, so the sample was honest and only the coverage was short.

DEDUPE IS NOT OPTIONAL AT THIS WIDTH. GHO regenerates the surrogate `Id` on
every row and its serialiser reorders keys between deploys: refetching all 384
September pages on 22 September found 377 changed at the byte level and 6
changed as data. Without `dedupe_canon` that is ~97 MB a month to preserve
~1.5 MB of movement, and the repo outgrows git inside a year.
"""
import csv, math, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASOF = "2026-09-22"
PAGE = 1000

TEMPLATE = """source_id: {sid}
status: active
cadence: monthly
schema_id: gho.v1

publisher: World Health Organization
publisher_tier: first_party
destroys_own_history: true   # a revision overwrites the previous value in place
licence: "CC BY-NC-SA 3.0 IGO; see https://www.who.int/about/policies/publishing/copyright"
personal_data: none
storage: git

# GHO's bytes move when its data does not: the surrogate `Id` is regenerated on
# every row and the serialiser reorders keys between deploys. Compare in
# canonical form and ignore the surrogate, or every capture stores a full copy
# of an unchanged series.
dedupe_canon: json
dedupe_ignore:
  - '"Id":\\s*\\d+,'

notes: >-
  {name}

  Every row carries a `Date` stamped when WHO last loaded the series, not when
  the observation refers to. Republishing restates the whole history and the
  previous values are gone — that is the perishable fact this captures.
  Last republished {lp} ({age} days before this entry was added);
  {rows:,} rows in {pages} page{s} at that point.

endpoints:
{endpoints}
gates:
  expect_status: 200
  min_bytes: 400
  content_type_any: [json]
  must_contain: ["IndicatorCode"]
  must_not_contain: ["\\"error\\""]
  # GHO restates whole series, so legitimate month-to-month movement is large.
  # 50% matches the fleet convention: high enough not to fire on a real change,
  # low enough to catch a truncated or empty response.
  max_shrink_pct: 50
"""

DEDUPE_BLOCK = """
# GHO's bytes move when its data does not: the surrogate `Id` is regenerated on
# every row and the serialiser reorders keys between deploys. Compare in
# canonical form and ignore the surrogate, or every capture stores a full copy
# of an unchanged series.
dedupe_canon: json
dedupe_ignore:
  - '"Id":\\s*\\d+,'
"""


def sid_of(code):
    return "who.gho." + code.lower().replace("_", "-")


def endpoints_for(code, rows):
    out = []
    for i in range(max(1, math.ceil(rows / PAGE))):
        q = f"?$top={PAGE}" + (f"&$skip={i*PAGE}" if i else "")
        out.append(f'  - url: "https://ghoapi.azureedge.net/api/{code}{q}"\n'
                   f"    delay_seconds: 2\n    timeout_seconds: 120\n")
    return "".join(out)


def main():
    reg = ROOT / "registry"
    sizes = {r["indicator_code"]: int(r["rows"])
             for r in csv.DictReader(open(ROOT / "data" / f"gho-active-sizes-{ASOF}.csv"))
             if r["rows"]}
    active = [r for r in csv.DictReader(open(ROOT / "data" / f"gho-activity-census-{ASOF}.csv"))
              if r["status"] == "ok" and int(r["days_since"]) < 365]
    made = patched = skipped = 0
    for r in active:
        code = r["indicator_code"]
        path = reg / f"{sid_of(code)}.yml"
        if path.exists():
            text = path.read_text()
            if "dedupe_canon" not in text:                 # retrofit the 48
                text = text.replace("\nstorage: git\n", "\nstorage: git\n" + DEDUPE_BLOCK)
                path.write_text(text)
                patched += 1
            else:
                skipped += 1
            continue
        rows = sizes.get(code)
        if not rows:
            continue
        pages = max(1, math.ceil(rows / PAGE))
        path.write_text(TEMPLATE.format(
            sid=sid_of(code), name=(r["indicator_name"] or code).strip(),
            lp=r["last_published"], age=r["days_since"], rows=rows,
            pages=pages, s="" if pages == 1 else "s",
            endpoints=endpoints_for(code, rows)))
        made += 1
    print(f"  active {len(active)}   new entries {made}   retrofitted {patched}   already done {skipped}")
    print(f"  registry now holds {len(list(reg.glob('*.yml')))} sources")


if __name__ == "__main__":
    main()
