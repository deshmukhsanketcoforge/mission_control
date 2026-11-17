"""Run the whole pipeline for one filed report.

Order: limits (code, already saved at filing) -> sort (model) -> three checks
(model, at the same time) -> brief-by time (code) -> draft and review loop
(model). Every step is written to the trace with its tokens, time and cost.

The pipeline can finish a report for a person to review, or mark it failed. It
cannot approve: that is a separate, human-only action (see services.py).
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.engine import Engine
from sqlmodel import Session, select

from app.domain.brief_time import Severity, brief_by_minutes, effective_severity
from app.domain.pricing import UnknownModelError, cost_usd, format_usd, total_cost
from app.domain.status import Actor, ReportStatus, transition
from app.llm.base import LLMClient
from app.llm.recording import CallRecord, RecordingClient
from app.models import Analysis, Report, TraceStep
from app.pipeline.briefing_loop import BriefingInput, LoopResult, run_briefing_loop
from app.pipeline.checks import (
    STEP_INJECTION,
    STEP_MISSING,
    STEP_PANIC,
    ChecksOutcome,
    run_checks,
)
from app.pipeline.sort import SortResult, sort_report


@dataclass
class _Step:
    step: str
    detail: str = ""
    round: int | None = None
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    status: str = "ok"
    cost: Decimal = Decimal(0)


class _Trace:
    """Collects trace rows: code steps added directly, model calls from the recorder."""

    def __init__(self, recorder: RecordingClient) -> None:
        self.steps: list[_Step] = []
        self._recorder = recorder
        self._seen = 0

    def code_step(self, step: str, detail: str) -> None:
        self.steps.append(_Step(step, detail))

    def collect(self, details: dict[tuple[str, int | None], str] | None = None) -> None:
        """Add rows for model calls made since the last collect."""
        details = details or {}
        for record in self._recorder.records[self._seen :]:
            self.steps.append(_model_step(record, details.get((record.step, record.round), "")))
        self._seen = len(self._recorder.records)

    @property
    def total(self) -> Decimal:
        return total_cost(s.cost for s in self.steps)


def _model_step(record: CallRecord, detail: str) -> _Step:
    cost, note = _price(record)
    if record.status == "error":
        detail = record.error or "The call failed."
    return _Step(
        step=record.step,
        round=record.round,
        model=record.model,
        input_tokens=record.input_tokens,
        output_tokens=record.output_tokens,
        latency_ms=record.latency_ms,
        status=record.status,
        cost=cost,
        detail=" ".join(part for part in (detail, note) if part),
    )


def _price(record: CallRecord) -> tuple[Decimal, str]:
    if record.model is None:
        return Decimal(0), ""
    try:
        return cost_usd(record.model, record.input_tokens, record.output_tokens), ""
    except UnknownModelError:
        return Decimal(0), f"No price known for model {record.model}; counted as 0."


async def run_pipeline(engine: Engine, report_id: int, client: LLMClient) -> None:
    with Session(engine) as session:
        report = session.get(Report, report_id)
        analysis = session.exec(select(Analysis).where(Analysis.report_id == report_id)).one()
        if analysis.status != ReportStatus.PROCESSING.value:
            return  # already finished, failed or interrupted: leave it alone
        data = report.model_dump()
        verdict = analysis.verdict
        violations = [dict(v) for v in analysis.violations]

    recorder = RecordingClient(client)
    trace = _Trace(recorder)
    trace.code_step(
        "limits",
        f"{verdict}; {len(violations)} violation{'' if len(violations) == 1 else 's'}",
    )

    try:
        sort = await sort_report(
            recorder, station=data["station"], wind_knots=data["wind_knots"],
            temp_c=data["temp_c"], fuel_pct=data["fuel_pct"], note=data["note"],
        )
        trace.collect({("sort", None): _sort_detail(sort)})

        checks = await run_checks(
            recorder, station=data["station"], wind_knots=data["wind_knots"],
            temp_c=data["temp_c"], fuel_pct=data["fuel_pct"], note=data["note"],
        )
        trace.collect(_check_details(checks))

        # A note that gives instructions cannot be trusted to rate itself:
        # its severity is not used and the report is briefed as high.
        severity_for_brief = Severity.HIGH if checks.hidden_instructions.flagged else sort.severity
        effective = effective_severity(severity_for_brief, len(violations))
        minutes = brief_by_minutes(severity_for_brief, len(violations))
        trace.code_step("brief_by", f"{minutes} minutes ({effective.value} severity)")

        loop = await run_briefing_loop(
            recorder,
            BriefingInput(
                station=data["station"], wind_knots=data["wind_knots"], temp_c=data["temp_c"],
                fuel_pct=data["fuel_pct"], note=data["note"], verdict=verdict,
                violations=[v["message"] for v in violations],
                subsystem=sort.subsystem.value, severity=effective.value,
                brief_by_minutes=minutes,
                flags=[r.name for r in checks.all if r.flagged],
            ),
        )
        trace.collect(_loop_details(loop))
    except Exception as err:  # the pipeline must never crash the background task
        trace.collect()
        _save(engine, report_id, trace, status=ReportStatus.FAILED, error=f"{type(err).__name__}: {err}")
        return

    reasons = _review_reasons(sort, checks, loop)
    _save(
        engine, report_id, trace, status=ReportStatus.PENDING_APPROVAL,
        subsystem=sort.subsystem.value, severity=sort.severity.value,
        effective_severity=effective.value, brief_by_minutes=minutes,
        checks=[
            {"name": r.name, "flagged": r.flagged, "reason": r.reason, "failed": r.failed}
            for r in checks.all
        ],
        needs_review=bool(reasons), review_reasons=reasons,
        briefing=loop.briefing, evaluator_passed=loop.passed, rounds=len(loop.rounds),
    )


def _review_reasons(sort: SortResult, checks: ChecksOutcome, loop: LoopResult) -> list[str]:
    reasons = []
    for result in checks.all:
        if result.failed:
            reasons.append(f"check_failed:{result.name}")
        elif result.name == "hidden_instructions" and result.flagged:
            reasons.append("hidden_instructions")
    if sort.fallback_used:
        reasons.append("sort_fallback")
    if not loop.passed:
        reasons.append("evaluator_not_passed")
    return reasons


def _sort_detail(sort: SortResult) -> str:
    text = f"{sort.subsystem.value} / {sort.severity.value}"
    return f"{text} (fallback: {sort.fallback_reason})" if sort.fallback_used else text


def _check_details(checks: ChecksOutcome) -> dict[tuple[str, int | None], str]:
    steps = {"hidden_instructions": STEP_INJECTION, "missing_details": STEP_MISSING, "panic_tone": STEP_PANIC}
    return {
        (steps[r.name], None): f"{'flagged' if r.flagged else 'not flagged'}: {r.reason}"
        for r in checks.all
    }


def _loop_details(loop: LoopResult) -> dict[tuple[str, int | None], str]:
    details: dict[tuple[str, int | None], str] = {}
    for r in loop.rounds:
        details[("draft", r.round)] = f"Round {r.round}" + (" (revised)" if r.round > 1 else "")
        details[("review", r.round)] = (
            "approved" if r.approved else f"rejected: {r.feedback}"
        )
    return details


def _save(engine: Engine, report_id: int, trace: _Trace, *, status: ReportStatus, error: str | None = None, **fields) -> None:
    with Session(engine) as session:
        analysis = session.exec(select(Analysis).where(Analysis.report_id == report_id)).one()
        analysis.status = transition(ReportStatus(analysis.status), status, Actor.SYSTEM).value
        analysis.error = error
        analysis.total_cost_usd = format_usd(trace.total)
        analysis.updated_at = datetime.now(timezone.utc)
        for name, value in fields.items():
            setattr(analysis, name, value)
        session.add(analysis)
        for seq, s in enumerate(trace.steps):
            session.add(
                TraceStep(
                    report_id=report_id, seq=seq, step=s.step, round=s.round, model=s.model,
                    input_tokens=s.input_tokens, output_tokens=s.output_tokens,
                    latency_ms=s.latency_ms, cost_usd=format_usd(s.cost),
                    status=s.status, detail=s.detail,
                )
            )
        session.commit()
