"""Request and response shapes for reports.

Validation lives here so every bad input is rejected with a clear message
before anything is saved.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Physical sanity ranges. These reject impossible input (typos, wrong units).
# They are NOT the launch limits; those are checked later in plain code.
WIND_RANGE = (0.0, 200.0)
TEMP_RANGE = (-90.0, 60.0)
FUEL_RANGE = (0.0, 100.0)


class ReportIn(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    station: str = Field(min_length=1, max_length=100)
    wind_knots: float
    temp_c: float
    fuel_pct: float
    note: str = Field(min_length=1, max_length=2000)

    @field_validator("wind_knots")
    @classmethod
    def _wind(cls, v: float) -> float:
        lo, hi = WIND_RANGE
        if not lo <= v <= hi:
            raise ValueError(f"Wind must be between {lo:g} and {hi:g} knots.")
        return v

    @field_validator("temp_c")
    @classmethod
    def _temp(cls, v: float) -> float:
        lo, hi = TEMP_RANGE
        if not lo <= v <= hi:
            raise ValueError(f"Temperature must be between {lo:g} and {hi:g} C.")
        return v

    @field_validator("fuel_pct")
    @classmethod
    def _fuel(cls, v: float) -> float:
        lo, hi = FUEL_RANGE
        if not lo <= v <= hi:
            raise ValueError(f"Fuel must be between {lo:g} and {hi:g} percent.")
        return v


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    station: str
    wind_knots: float
    temp_c: float
    fuel_pct: float
    note: str
    created_at: datetime


def report_fields(report) -> dict:
    """A report row as a plain dict. Merge extra values over it with ``{**fields, "x": 1}``."""
    return ReportOut.model_validate(report).model_dump()


class ReportCreated(ReportOut):
    """What filing returns: the report plus the plain-code verdict, available at once."""

    status: str
    verdict: str
    violations: list["ViolationOut"]


class ApproveIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    approved_by: str = Field(min_length=1, max_length=100)


class ViolationOut(BaseModel):
    field: str
    value: float
    limit: str
    message: str


class CheckOut(BaseModel):
    name: str
    flagged: bool
    reason: str
    failed: bool = False


class TraceStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq: int
    step: str
    round: int | None
    model: str | None
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: str
    status: str
    detail: str


class AnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    verdict: str
    violations: list[ViolationOut]
    subsystem: str | None
    severity: str | None
    effective_severity: str | None
    brief_by_minutes: int | None
    checks: list[CheckOut]
    needs_review: bool
    review_reasons: list[str]
    briefing: str | None
    evaluator_passed: bool | None
    rounds: int
    total_cost_usd: str
    error: str | None
    approved_by: str | None
    approved_at: datetime | None


class ReportListItem(ReportOut):
    status: str
    verdict: str
    brief_by_minutes: int | None
    needs_review: bool
    total_cost_usd: str


class ReportDetail(ReportOut):
    analysis: AnalysisOut
    trace: list[TraceStepOut]
