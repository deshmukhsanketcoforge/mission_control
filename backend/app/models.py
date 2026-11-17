from datetime import datetime, timezone

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
