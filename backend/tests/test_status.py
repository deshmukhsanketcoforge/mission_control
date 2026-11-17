"""Only a person can approve a briefing. The rule lives in one function."""

import pytest

from app.domain.status import (
    Actor,
    InvalidTransition,
    NotPermitted,
    ReportStatus,
    transition,
)

S = ReportStatus


def test_pipeline_can_finish_a_report_for_review():
    assert transition(S.PROCESSING, S.PENDING_APPROVAL, Actor.SYSTEM) == S.PENDING_APPROVAL


def test_pipeline_can_mark_a_report_failed():
    assert transition(S.PROCESSING, S.FAILED, Actor.SYSTEM) == S.FAILED


def test_a_person_can_approve_a_pending_briefing():
    assert transition(S.PENDING_APPROVAL, S.APPROVED, Actor.HUMAN) == S.APPROVED


@pytest.mark.parametrize("current", list(ReportStatus))
def test_the_pipeline_can_never_approve_from_any_state(current):
    with pytest.raises((NotPermitted, InvalidTransition)):
        transition(current, S.APPROVED, Actor.SYSTEM)


def test_pipeline_approval_is_refused_even_from_pending():
    with pytest.raises(NotPermitted):
        transition(S.PENDING_APPROVAL, S.APPROVED, Actor.SYSTEM)


@pytest.mark.parametrize("current", [S.PROCESSING, S.FAILED, S.APPROVED])
def test_only_a_pending_briefing_can_be_approved(current):
    with pytest.raises(InvalidTransition):
        transition(current, S.APPROVED, Actor.HUMAN)


@pytest.mark.parametrize("target", list(ReportStatus))
def test_an_approved_report_is_final(target):
    for actor in Actor:
        with pytest.raises(InvalidTransition):
            transition(S.APPROVED, target, actor)


@pytest.mark.parametrize("target", [S.PROCESSING, S.PENDING_APPROVAL])
def test_a_failed_report_cannot_move_on(target):
    with pytest.raises(InvalidTransition):
        transition(S.FAILED, target, Actor.SYSTEM)


def test_a_pending_briefing_cannot_go_back_to_processing():
    with pytest.raises(InvalidTransition):
        transition(S.PENDING_APPROVAL, S.PROCESSING, Actor.SYSTEM)
