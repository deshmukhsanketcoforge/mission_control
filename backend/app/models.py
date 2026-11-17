from datetime import datetime, timezone

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Report(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    station: str
    wind_knots: float
    temp_c: float
    fuel_pct: float
    note: str
    created_at: datetime = Field(default_factory=_now)


class Analysis(SQLModel, table=True):
    """What the pipeline concluded about one report. One row per report.

    Kept apart from ``Report`` so the filed report stays exactly as the engineer
    sent it, and so databases from earlier versions need no migration.
    """

    id: int | None = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="report.id", unique=True, index=True)
    status: str  # see app.domain.status.ReportStatus
    verdict: str  # "go" or "no_go", from plain code
    violations: list = Field(default_factory=list, sa_column=Column(JSON))

    subsystem: str | None = None
    severity: str | None = None  # what the model said
    effective_severity: str | None = None  # after violations and flags are applied
    brief_by_minutes: int | None = None

    checks: list = Field(default_factory=list, sa_column=Column(JSON))
    needs_review: bool = False
    review_reasons: list = Field(default_factory=list, sa_column=Column(JSON))

    briefing: str | None = None
    evaluator_passed: bool | None = None
    rounds: int = 0

    total_cost_usd: str = "0"  # exact decimal text
    error: str | None = None

    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class TraceStep(SQLModel, table=True):
    """One card in the Flight Director's trace: a step the pipeline took."""

    id: int | None = Field(default=None, primary_key=True)
    report_id: int = Field(foreign_key="report.id", index=True)
    seq: int
    step: str
    round: int | None = None
    model: str | None = None  # None for steps done in plain code
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    cost_usd: str = "0"  # exact decimal text
    status: str = "ok"  # "ok" or "error"
    detail: str = ""
