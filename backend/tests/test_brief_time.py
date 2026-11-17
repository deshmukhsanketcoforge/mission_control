"""Brief-by time follows severity. Any limit violation counts as high."""

import pytest

from app.domain.brief_time import Severity, brief_by_minutes, effective_severity
from app.domain.limits import check_limits


@pytest.mark.parametrize(
    "severity,minutes",
    [(Severity.HIGH, 5), (Severity.MEDIUM, 15), (Severity.LOW, 30)],
)
def test_minutes_follow_severity(severity, minutes):
    assert brief_by_minutes(severity, violation_count=0) == minutes


@pytest.mark.parametrize("severity", list(Severity))
def test_any_violation_forces_five_minutes(severity):
    assert brief_by_minutes(severity, violation_count=1) == 5
    assert brief_by_minutes(severity, violation_count=3) == 5


@pytest.mark.parametrize("severity", list(Severity))
def test_effective_severity_is_high_with_a_violation(severity):
    assert effective_severity(severity, violation_count=1) == Severity.HIGH


@pytest.mark.parametrize("severity", list(Severity))
def test_effective_severity_is_unchanged_without_violations(severity):
    assert effective_severity(severity, violation_count=0) == severity


def test_works_with_real_limit_results():
    clean = check_limits(wind_knots=10, temp_c=20, fuel_pct=99)
    bad = check_limits(wind_knots=26, temp_c=20, fuel_pct=99)
    assert brief_by_minutes(Severity.LOW, len(clean.violations)) == 30
    assert brief_by_minutes(Severity.LOW, len(bad.violations)) == 5


def test_negative_violation_count_is_rejected():
    with pytest.raises(ValueError):
        brief_by_minutes(Severity.LOW, violation_count=-1)
