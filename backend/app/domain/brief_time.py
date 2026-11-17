"""Brief-by time: how many minutes the Flight Director has to be briefed."""

from enum import StrEnum


class Severity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


BRIEF_BY_MINUTES: dict[Severity, int] = {
    Severity.HIGH: 5,
    Severity.MEDIUM: 15,
    Severity.LOW: 30,
}


def effective_severity(severity: Severity, violation_count: int) -> Severity:
    """Any launch-limit violation counts as high, whatever the model said."""
    _check_count(violation_count)
    return Severity.HIGH if violation_count > 0 else severity


def brief_by_minutes(severity: Severity, violation_count: int) -> int:
    """5, 15 or 30 minutes for high, medium or low. Any violation gives 5."""
    return BRIEF_BY_MINUTES[effective_severity(severity, violation_count)]


def _check_count(violation_count: int) -> None:
    if violation_count < 0:
        raise ValueError("violation_count cannot be negative")
