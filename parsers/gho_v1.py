"""Parser for schema_id `gho.v1` — WHO Global Health Observatory OData.

WHAT MAKES THIS ARCHIVE WORTH KEEPING

WHO restates history. Under-five mortality for Brazil in 1931 carries
`Date: 2026-08-05` — a 95-year-old figure rewritten last month, along with all
64,510 rows of that indicator. The previous values are gone, and every paper
citing them is citing a number that can no longer be checked.

So the observation is *(indicator, country, reference year)* and the thing that
moves is its VALUE. A revision must therefore appear as the same entity and
metric carrying a different value at a later capture — not as a new row.

TWO CHOICES THAT FOLLOW

`observed_at` is the **reference year**, not the fetch time and not `Date`.
A row describes child mortality in 2005; that is when the observation is about.
Using the fetch time would stamp an unchanged series with a new timestamp every
month and invent movement that never happened.

`Date` — WHO's own load stamp — is carried as its own metric, `restated_at`.
It is the evidence that a revision occurred and when, which is the whole point,
and it is stamped per load batch rather than per row, so it can move while the
value does not.

DIMENSIONS ARE NOT UNIFORM. Under-five mortality has SEX, AGEGROUP and
WEALTHQUINTILE; measles immunisation has none and is not even country-keyed
(WORLDBANKINCOMEGROUP). Filtering on a dimension an indicator lacks returns
zero rows with NO error, so nothing is filtered at capture time and the
breakdown is preserved in the entity id instead.
"""

import json

from wss import derive

PARSER_VERSION = "2"
SCHEMA_ID = "gho.v1"

# Dimension slots that vary per indicator. Included in the entity id only when
# present, so a one-dimensional indicator does not grow empty separators.
_DIMS = ("Dim1", "Dim2", "Dim3")


def _entity(row):
    """indicator:country[:dim...] — stable across captures, unique within one."""
    parts = [row.get("IndicatorCode") or "?", str(row.get("SpatialDim") or "?")]
    for d in _DIMS:
        v = row.get(d)
        if v:
            parts.append(str(v))
    return ":".join(parts)


def _year(row):
    """The reference year the observation is about."""
    v = row.get("TimeDim")
    if v in (None, ""):
        return None
    try:
        y = int(v)
    except (TypeError, ValueError):
        return None
    return f"{y:04d}-01-01" if 1800 <= y <= 2100 else None


def parse(body: bytes, ctx: derive.ParseContext):
    payload = json.loads(body)
    for row in payload.get("value", []):
        observed_at = _year(row)
        if observed_at is None:
            continue
        entity = _entity(row)

        # Not every indicator is numeric. The policy inventories -- alcohol
        # licensing, beverage tax bands -- answer "Yes", "No", "Not Applicable"
        # and carry NumericValue: null. Version 1 emitted nothing for those, so
        # six of forty-eight indicators lost their data silently while their
        # restated_at rows kept arriving and made the series look present.
        value = row.get("NumericValue")
        if value is not None:
            yield derive.Observation(
                entity_id=entity, metric="value", value=float(value),
                unit="", observed_at=observed_at,
            )
        elif row.get("Value") not in (None, ""):
            yield derive.Observation(
                entity_id=entity, metric="value", value=str(row["Value"])[:120],
                unit="", observed_at=observed_at,
            )

        # Published uncertainty, independent of whether the value was numeric.
        # A wide band means the figure is modelled rather than registered, and
        # modelled figures are the ones that move -- so the band is what the
        # revision prediction is tested against.
        for metric, key in (("low", "Low"), ("high", "High")):
            bound = row.get(key)
            if bound is None:
                continue
            try:
                yield derive.Observation(
                    entity_id=entity, metric=metric, value=float(bound),
                    unit="", observed_at=observed_at,
                )
            except (TypeError, ValueError):
                pass

        # WHO's own load stamp: when this series was last written. Carried as a
        # metric because a restatement is the event being recorded.
        restated = row.get("Date")
        if restated:
            yield derive.Observation(
                entity_id=entity, metric="restated_at", value=str(restated)[:10],
                unit="", observed_at=observed_at,
            )


derive.register(SCHEMA_ID, parse, PARSER_VERSION)
