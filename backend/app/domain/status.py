"""Report status and the rule that only a person can approve a briefing.

Every status change goes through ``transition``. The pipeline acts as
``Actor.SYSTEM`` and is refused when it tries to approve. The approve endpoint
acts as ``Actor.HUMAN``.
"""

from enum import StrEnum


class ReportStatus(StrEnum):
    PROCESSING = "processing"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    FAILED = "failed"


class Actor(StrEnum):
    SYSTEM = "system"
    HUMAN = "human"


class InvalidTransition(Exception):
    """The move is not allowed from the current status."""


class NotPermitted(Exception):
    """This actor is not allowed to make this move."""


_ALLOWED: dict[ReportStatus, set[ReportStatus]] = {
    ReportStatus.PROCESSING: {ReportStatus.PENDING_APPROVAL, ReportStatus.FAILED},
    ReportStatus.PENDING_APPROVAL: {ReportStatus.APPROVED},
    ReportStatus.APPROVED: set(),
    ReportStatus.FAILED: set(),
}


def transition(current: ReportStatus, target: ReportStatus, actor: Actor) -> ReportStatus:
    if target not in _ALLOWED[current]:
        raise InvalidTransition(f"Cannot move a report from {current} to {target}")
    if target == ReportStatus.APPROVED and actor != Actor.HUMAN:
        raise NotPermitted("Only a person can approve a briefing")
    return target
