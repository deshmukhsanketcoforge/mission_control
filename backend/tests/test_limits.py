"""Launch limits are checked in plain code. Each limit is tested exactly on the
limit and just past it.

Limits: wind <= 25 kt, temp >= 4 C, fuel 98..100 %.
"""

import math

import pytest

from app.domain.limits import GO, NO_GO, check_limits

OK = dict(wind_knots=10, temp_c=20, fuel_pct=99)


def run(**overrides):
    return check_limits(**{**OK, **overrides})


def fields(result):
    return [v.field for v in result.violations]


def test_all_readings_inside_limits_is_go():
    result = run()
    assert result.verdict == GO
    assert result.violations == []


# --- wind: 25 knots or less ------------------------------------------------
@pytest.mark.parametrize("wind", [0, 24.99, 25])
def test_wind_at_or_below_limit_passes(wind):
    result = run(wind_knots=wind)
    assert result.verdict == GO
    assert "wind_knots" not in fields(result)


@pytest.mark.parametrize("wind", [25.01, 26, 60])
def test_wind_just_past_limit_is_no_go(wind):
    result = run(wind_knots=wind)
    assert result.verdict == NO_GO
    assert fields(result) == ["wind_knots"]


# --- temperature: 4 C or more ----------------------------------------------
@pytest.mark.parametrize("temp", [4, 4.01, 30])
def test_temp_at_or_above_limit_passes(temp):
    result = run(temp_c=temp)
    assert result.verdict == GO
    assert "temp_c" not in fields(result)


@pytest.mark.parametrize("temp", [3.99, 0, -20])
def test_temp_just_past_limit_is_no_go(temp):
    result = run(temp_c=temp)
    assert result.verdict == NO_GO
    assert fields(result) == ["temp_c"]


# --- fuel: 98 to 100 percent -----------------------------------------------
@pytest.mark.parametrize("fuel", [98, 98.01, 99.5, 100])
def test_fuel_inside_band_passes(fuel):
    result = run(fuel_pct=fuel)
    assert result.verdict == GO
    assert "fuel_pct" not in fields(result)


@pytest.mark.parametrize("fuel", [97.99, 50, 0, 100.01, 120])
def test_fuel_just_outside_band_is_no_go(fuel):
    result = run(fuel_pct=fuel)
    assert result.verdict == NO_GO
    assert fields(result) == ["fuel_pct"]


# --- several violations ----------------------------------------------------
def test_every_violation_is_reported():
    result = run(wind_knots=30, temp_c=0, fuel_pct=90)
    assert result.verdict == NO_GO
    assert fields(result) == ["wind_knots", "temp_c", "fuel_pct"]


def test_violation_carries_value_limit_and_message():
    (v,) = run(wind_knots=30).violations
    assert v.field == "wind_knots"
    assert v.value == 30
    assert "25" in v.limit
    assert "30" in v.message and "25" in v.message


# --- fail safe -------------------------------------------------------------
@pytest.mark.parametrize("field", ["wind_knots", "temp_c", "fuel_pct"])
@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_non_finite_reading_is_a_violation_not_a_pass(field, bad):
    result = run(**{field: bad})
    assert result.verdict == NO_GO
    assert field in fields(result)


# --- the verdict comes from the numbers only -------------------------------
def test_check_limits_takes_no_note_or_model_input():
    """A note can never reach the verdict: the function has no parameter for it."""
    import inspect

    params = set(inspect.signature(check_limits).parameters)
    assert params == {"wind_knots", "temp_c", "fuel_pct"}
