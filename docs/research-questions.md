# What a WHO GHO vintage archive would be for

Written before the repo, because the rule is probe, write the questions down,
try to answer them, and only then decide what to build. Screening evidence is in
[`../screening-log.md`](../screening-log.md).

## The spine

**WHO rewrites its own history and keeps no vintages.** Under-five mortality for
Brazil in **1931** carries `Date: 2026-08-05` — a 95-year-old figure restated
last month, together with all 64,510 rows of that indicator. The previous values
are gone.

Everyone cites these numbers. Nobody can check what they used to say.

## The questions

Status is honest about what can be answered **today** against what needs the
archive to exist.

| # | question | needs | status |
| --- | --- | --- | --- |
| 1 | Which indicators are maintained and which are abandoned? | one capture | **answered** — 14.2% republished within a year (CI 10.9–18.4%), median 4.7 years |
| 2 | How uncertain are the estimates, and for whom? | one capture | **answered** — non-G20 intervals 2.3× wider on the rows we capture |
| 3 | **Does WHO restate continuously, or in releases?** | one capture | **answered** — in batches. 25 distinct dates across 48 indicators; **71% share a date with another**. Roughly two release events a month |
| 4 | How far back does WHO model? | one capture | **answered** — the flagship reaches 1931, but 71% of all values are post-2000 and only 8 of 48 indicators span 30+ years. Six are a single year |
| 5 | How much of GHO is aggregate rather than observation? | one capture | **answered** — **9.1%** of rows are regional or income-group aggregates; 90.9% are country rows across 230 places |
| 6 | **How far does a restated number move?** | **two captures** | **the point of the archive** — first answer possible next month |
| 7 | How far back does a revision reach — recent years, or the whole series? | two captures | next month |
| 8 | Which countries' history is rewritten most? | a year | accruing — **prediction recorded below** |
| 9 | Is revision directionally biased? Does progress look better in hindsight? | two years | accruing |
| 10 | **Do SDG baselines move?** | two years | accruing |
| 11 | Which indicators are stable enough to cite, and which are not? | a year | accruing |
| 12 | When a paper cites "WHO's estimate for year Y", is it still checkable? | a year | accruing |
| 13 | Are indicators ever **deleted** from the catalogue? | a year | accruing — a dormant indicator still shows; a removed one vanishes without trace |
| 15 | **Which indicators are reliable enough to cite at all?** | one capture | **answered** — median band runs from ±17% (infant deaths) to **±111%** (air pollution attributable death rate), ordered almost exactly counted-first, modelled-last |
| 14 | *Why* a revision happened | WHO methodology notes, not in the API | **blocked** |

**Nine of fourteen need the series observed over time**, and the first of them
— question 6, the one the repo exists for — is answerable at the second
capture rather than after a year. That is why this is a capture and not a
recipe, and why the clock mattered more than the scope.

## Question 9 is the one that matters

SDG progress is measured against a **2015 baseline**. If WHO revises the 2015
value, measured progress changes although nothing in the world did. Nobody can
currently say how often that happens, because the previous baseline is not
retained anywhere.

An archive answers it directly: hold the 2015 figure as published in each
vintage, and watch it move.

## A falsifiable prediction, recorded before the data exists

From question 2: uncertainty intervals are **1.8× wider outside the G20**
(median 39.9% of the estimate against 21.6%). A wide interval means the figure
is modelled rather than registered, and models are what change when they are
updated.

> **Prediction: revision magnitude will correlate with interval width, so
> countries with the weakest vital registration will have their history
> rewritten most.**

If that holds, it has a consequence worth stating in advance: the countries whose
numbers are least stable are the ones most written about in development
research. If it fails, the scoping assumption behind this repo is wrong and the
capture should widen rather than narrow.

**It also rules out one tempting economy.** Downsampling to G20 or "critical
regions" would keep the countries whose numbers barely move and discard the
ones that get revised — it selects against the signal. Geographic downsampling
is the one cut this source cannot take.

## Scope, and what it costs us

Measured, not assumed: 48 of 337 sampled indicators are active, totalling
**355,621 rows**; median 2,599, and 35 of the 48 are under 5,000 rows. The two
mortality giants are outliers.

**Decision.** Capture `SpatialDimType=COUNTRY`, `Dim1=SEX_BTSX`,
`Dim3=WEALTHQUINTILE_TOTL` — roughly a quarter of the rows, and every number
anyone actually cites.

**Vulnerability.** A revision confined to the sex or wealth breakdown, leaving
totals unchanged, is **invisible to us**. We would report "no revision" wrongly.

**Limit.** This is not a mirror of GHO. It keeps the cited headline series, not
the published grid.

**Exit.** If a revision is ever found that moved a breakdown without moving the
total, the scope was wrong and the capture widens. If after a year no indicator
has moved by more than its own rounding, the premise is wrong and this goes to
the graveyard.

## Two API constraints any design must respect

- **`$top` caps at 1,000**, so every indicator needs paging — 65 requests for
  under-five mortality alone.
- **Cold indicators take ~42 s**, and eight in parallel still return as a ~62 s
  batch. Throughput is ~8 per minute regardless of concurrency, which is a
  server-side queue rather than latency.
