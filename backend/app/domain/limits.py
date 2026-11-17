"""Launch limits, checked in plain code.

No model is involved here, and the free-text note is not an input. The verdict
depends only on the three readings.

Limits:
    wind_knots  <= 25
    temp_c      >= 4
    fuel_pct    between 98 and 100, inclusive
"""

import math
from dataclasses import dataclass, field
from typing import Literal

GO = "go"
NO_GO = "no_go"

WIND_MAX_KNOTS = 25.0
TEMP_MIN_C = 4.0
FUEL_MIN_PCT = 98.0
FUEL_MAX_PCT = 100.0

Verdict = Literal["go", "no_go"]


@dataclass(frozen=True)
class Violation:
    field: str
    value: float
    limit: str
    message: str


@dataclass(frozen=True)
class LimitsResult:
    verdict: Verdict
    violations: list[Violation] = field(default_factory=list)


def check_limits(*, wind_knots: float, temp_c: float, fuel_pct: float) -> LimitsResult:
    """Compare the readings with the launch limits.

    Any reading outside its limit makes the verdict ``no_go``. A reading that is
    not a finite number (NaN, infinity) is treated as a violation, because
    comparisons with NaN are always False and would otherwise pass silently.
    """
    violations: list[Violation] = []

    if not _ok(wind_knots) or wind_knots > WIND_MAX_KNOTS:
        violations.append(
            Violation(
                "wind_knots",
                wind_knots,
                f"<= {WIND_MAX_KNOTS:g} knots",
                f"Wind {wind_knots:g} knots is above the {WIND_MAX_KNOTS:g} knot limit.",
            )
        )

    if not _ok(temp_c) or temp_c < TEMP_MIN_C:
        violations.append(
            Violation(
                "temp_c",
                temp_c,
                f">= {TEMP_MIN_C:g} C",
                f"Temperature {temp_c:g} C is below the {TEMP_MIN_C:g} C limit.",
            )
        )

    if not _ok(fuel_pct) or not FUEL_MIN_PCT <= fuel_pct <= FUEL_MAX_PCT:
        violations.append(
            Violation(
                "fuel_pct",
                fuel_pct,
                f"{FUEL_MIN_PCT:g} to {FUEL_MAX_PCT:g} %",
                f"Fuel {fuel_pct:g}% is outside the {FUEL_MIN_PCT:g} to {FUEL_MAX_PCT:g}% band.",
            )
        )

    return LimitsResult(verdict=NO_GO if violations else GO, violations=violations)


def _ok(value: float) -> bool:
    return math.isfinite(value)
