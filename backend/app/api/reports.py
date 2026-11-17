"""Routes for filing, reading and approving reports."""

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlmodel import Session, select

from app.api.deps import get_session
from app.api.errors import error_response
from app.domain.status import InvalidTransition
from app.models import Analysis, Report, TraceStep
from app.pipeline.runner import run_pipeline
from app.schemas import (
    AnalysisOut,
    ApproveIn,
    ReportDetail,
    ReportIn,
    ReportListItem,
    ReportOut,
)
from app.services import ReportNotFound, approve_report, file_report, get_analysis

router = APIRouter(prefix="/reports")


def _not_found():
    return error_response(404, "report", "Report not found.")


@router.post("", response_model=ReportOut, status_code=201)
def create_report(
    payload: ReportIn,
    request: Request,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
):
    report, _ = file_report(session, payload)
    # The pipeline runs after the response, so filing returns right away.
    background.add_task(
        run_pipeline, request.app.state.engine, report.id, request.app.state.llm_client
    )
    return report


@router.get("", response_model=list[ReportListItem])
def list_reports(session: Session = Depends(get_session)):
    rows = session.exec(
        select(Report, Analysis)
        .join(Analysis, Analysis.report_id == Report.id)
        .order_by(Report.id.desc())
    ).all()
    return [
        ReportListItem(
            **ReportOut.model_validate(report).model_dump(),
            status=analysis.status,
            verdict=analysis.verdict,
            brief_by_minutes=analysis.brief_by_minutes,
            needs_review=analysis.needs_review,
            total_cost_usd=analysis.total_cost_usd,
        )
        for report, analysis in rows
    ]


@router.get("/{report_id}", response_model=ReportDetail)
def report_detail(report_id: int, session: Session = Depends(get_session)):
    report = session.get(Report, report_id)
    if report is None:
        return _not_found()
    trace = session.exec(
        select(TraceStep).where(TraceStep.report_id == report_id).order_by(TraceStep.seq)
    ).all()
    return ReportDetail(
        **ReportOut.model_validate(report).model_dump(),
        analysis=AnalysisOut.model_validate(get_analysis(session, report_id)),
        trace=trace,
    )


@router.post("/{report_id}/approve", response_model=AnalysisOut)
def approve(report_id: int, payload: ApproveIn, session: Session = Depends(get_session)):
    """The only way a briefing becomes approved, and only a person calls it."""
    try:
        return approve_report(session, report_id, payload.approved_by)
    except ReportNotFound:
        return _not_found()
    except InvalidTransition:
        status = get_analysis(session, report_id).status
        message = (
            "This report is already approved."
            if status == "approved"
            else f"A report that is {status} cannot be approved."
        )
        return error_response(409, "status", message)
