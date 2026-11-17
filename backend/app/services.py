"""Database operations on reports. The API calls these; so do the tests."""

from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.domain.limits import check_limits
from app.domain.status import Actor, ReportStatus, transition
from app.models import Analysis, Report
from app.schemas import ReportIn

INTERRUPTED = "Interrupted by a restart before it finished."


class ReportNotFound(Exception):
    pass


def file_report(session: Session, payload: ReportIn) -> tuple[Report, Analysis]:
    """Save a report and its launch verdict.

    The verdict and violations come from plain code and are saved straight away,
    before any model is called, so they are never missing or model-made.
    """
    report = Report(**payload.model_dump())
    session.add(report)
    session.flush()

    limits = check_limits(
        wind_knots=report.wind_knots, temp_c=report.temp_c, fuel_pct=report.fuel_pct
    )
    analysis = Analysis(
        report_id=report.id,
        status=ReportStatus.PROCESSING.value,
        verdict=limits.verdict,
        violations=[asdict(v) for v in limits.violations],
    )
    session.add(analysis)
    session.commit()
    session.refresh(report)
    session.refresh(analysis)
    return report, analysis


def get_analysis(session: Session, report_id: int) -> Analysis:
    analysis = session.exec(select(Analysis).where(Analysis.report_id == report_id)).first()
    if analysis is None:
        raise ReportNotFound(report_id)
    return analysis


def approve_report(session: Session, report_id: int, approved_by: str) -> Analysis:
    """A person approves a pending briefing. The only code that can."""
    analysis = get_analysis(session, report_id)
    analysis.status = transition(
        ReportStatus(analysis.status), ReportStatus.APPROVED, Actor.HUMAN
    ).value
    now = datetime.now(timezone.utc)
    analysis.approved_by = approved_by
    analysis.approved_at = now
    analysis.updated_at = now
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return analysis


def recover_interrupted(engine: Engine) -> int:
    """Reports still processing when the app starts were cut off. Mark them failed."""
    with Session(engine) as session:
        stuck = session.exec(
            select(Analysis).where(Analysis.status == ReportStatus.PROCESSING.value)
        ).all()
        for analysis in stuck:
            analysis.status = transition(
                ReportStatus.PROCESSING, ReportStatus.FAILED, Actor.SYSTEM
            ).value
            analysis.error = INTERRUPTED
            session.add(analysis)
        session.commit()
        return len(stuck)
