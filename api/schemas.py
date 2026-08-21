from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field, field_validator


NonNegativeTonnes = Annotated[
    float,
    Field(ge=0)
]


class ForecastRequest(BaseModel):
    site_id: str = Field(
        pattern=r"^SITE_\d{3}$",
        examples=["SITE_001"]
    )

    forecast_origin_week: date | None = Field(
        default=None,
        description=(
            "Monday representing the forecast origin. "
            "The latest usable week is selected when omitted."
        ),
        examples=["2024-12-23"]
    )

    planned_pour_tonnes: list[NonNegativeTonnes] = Field(
        min_length=8,
        max_length=8,
        description=(
            "Planned pour tonnage for forecast "
            "Weeks 1 through 8."
        ),
        examples=[
            [150, 160, 155, 170, 165, 175, 180, 172]
        ]
    )

    @field_validator("forecast_origin_week")
    @classmethod
    def origin_must_be_monday(
        cls,
        value: date | None
    ) -> date | None:

        if value is not None and value.weekday() != 0:
            raise ValueError(
                "forecast_origin_week must be a Monday"
            )

        return value


class WeeklyForecast(BaseModel):
    horizon_week: int
    forecast_week_start: date
    planned_pour_tonnes: float
    predicted_demand_tonnes: float


class ForecastResponse(BaseModel):
    model_name: str = (
        "Schedule-Informed Random Forest"
    )

    site_id: str
    forecast_origin_week: date
    forecasts: list[WeeklyForecast]


class SiteInfo(BaseModel):
    site_id: str
    region: str
    behavior: str
    latest_forecast_origin_week: date


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    horizons: list[int]
    number_of_sites: int
    source_data_through: date | None