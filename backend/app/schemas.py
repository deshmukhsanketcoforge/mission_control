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
