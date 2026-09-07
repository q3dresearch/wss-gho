# reference

Screening evidence, taken before the first capture and kept because the
registry's scope rests on it.

- `indicator-activity-2026-09-07.csv` — 400 indicators drawn at random from the
  3,098 in the catalogue, each polled for when it was last republished. This is
  what says **14.2% are active** (95% CI 10.9–18.4%) and the median indicator
  has not been touched in **4.7 years**.

  **Drawn at random, not chosen.** Three earlier estimates taken from
  indicators picked by hand were wrong by up to 15× — the hand-picked median
  was 102 days against a true 4.7 years, because the famous indicators are
  exactly the maintained ones.

- `indicator-sizes-2026-09-07.csv` — row counts for the 48 active indicators.
  This is what the registry captures, and where the ~48 minute, ~89 MB capture
  budget comes from.

Both are re-derivable with `../examples/map_activity.py` and
`../examples/size_active.py`.

- `country-names-2026-09-07.csv` — the GHO COUNTRY dimension: code, name and WHO
  region for 234 places. Cached because the derived tables carry spatial codes
  but no names, and a chart script that has to reach the network cannot
  regenerate the same output later or run in CI.
