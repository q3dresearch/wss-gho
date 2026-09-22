# reference

Screening evidence, taken before the first capture and kept because the
registry's scope rests on it.

## Scope: which indicators are alive

- `indicator-activity-census-2026-09-22.csv` — **all 3,099** indicators in the
  catalogue, each polled for when WHO last reloaded it. **442 (14.3%) had been
  republished within a year**; the median dated indicator has not been touched
  in 4.4 years, and **612 are catalogued but hold no rows at all**. This is
  what the registry's 442 entries are.

- `indicator-activity-2026-09-07.csv` — the earlier 400-indicator random sample
  this replaced. Kept because it is the control: it put the active share at
  **14.2% (95% CI 10.9–18.4%)** against the census's 14.3%. The draw was
  honest; only the coverage was short.

  **Drawn at random, not chosen.** Three earlier estimates taken from
  indicators picked by hand were wrong by up to 15× — the hand-picked median
  was 102 days against a true 4.4 years, because the famous indicators are
  exactly the maintained ones.

  **Why it was a sample at all.** `map_activity.py` costed a census at ~6.7
  hours and sampled instead. That number was wrong by 136×: it was timing this
  host's IPv6 blackhole, not WHO. The tell was flat latency — batches of 6, 16
  and 32 all returned in ~136s, and `$select`, `$filter` and `$apply` cost the
  same as `$orderby`. Forcing AF_INET drops a request to ~1.0s and the census
  to **4m11s**. A sampling design can rest on a measurement artifact; this one
  did, for two weeks.

- `indicator-sizes-2026-09-22.csv` — row counts for the 442 active indicators:
  **3,084,631 rows**, median 2,489, max 96,876, and the ten largest are 26% of
  all rows. At GHO's hard `$top=1000` cap (anything larger is a 400) that is
  **3,321 pages** per capture. `indicator-sizes-2026-09-07.csv` is the same for
  the original 48.

## Why the registry sets `dedupe_canon`

- `serialisation-churn-2026-09-22.csv` — every one of the 384 pages captured on
  7 September, refetched on the 22nd and sorted three ways:

  | | pages | |
  |---|---|---|
  | bytes identical | 7 | 1.8% |
  | **data identical, bytes changed** | **371** | **96.6%** |
  | data changed | 6 | 1.6% |

  GHO regenerates the surrogate `Id` on every row, and its serialiser reorders
  keys between deploys — between these two dates `TimeDim` moved two keys left
  in every row. Neither is data. Byte-level dedupe therefore never fires:
  **98.2% of pages change, 1.6% mean anything**, and at 442 sources that is
  ~97 MB a month to preserve ~1.5 MB of movement, or 1.14 GB a year in a git
  repository.

  `dedupe_ignore` alone cannot fix it — it strips substrings and cannot survive
  reordering. `dedupe_canon: json` (wss-engine 0.6.55) compares the parsed body
  with sorted keys, and the two settings compose: the registry canonicalises,
  then strips `"Id":\s*\d+,`. **The stored bytes and `content_sha256` are
  always the untouched response**; canonical form exists only to answer changed
  vs unchanged.

  The two indicators that really moved, `NTD_LEPR3` and `NTD_LEPR8`, are the
  first revisions this repository has observed.

- `country-names-2026-09-07.csv` — the GHO COUNTRY dimension: code, name and WHO
  region for 234 places. Cached because the derived tables carry spatial codes
  but no names, and a chart script that has to reach the network cannot
  regenerate the same output later or run in CI.

Re-derivable with `../examples/map_activity.py` (`GHO_SAMPLE=all`),
`../examples/size_active.py` and `../examples/measure_churn.py`.
