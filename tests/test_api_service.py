from datetime import date

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from api.model_service import (
    ForecastNotFoundError,
    ForecastService
)

from api.schemas import ForecastRequest


class ConstantModel:
    """Small test model used instead of the 892 MB model."""

    def predict(
        self,
        input_data
    ):

        schedule_value = (
            input_data
            .iloc[0]
            .filter(
                like="planned_pour_week_"
            )
            .sum()
        )

        return np.array(
            [100.0 + schedule_value]
        )


def create_test_service():

    service = ForecastService()

    service.models = {
        horizon: ConstantModel()
        for horizon in range(1, 9)
    }

    service.features_by_horizon = {
        horizon: [
            "year",
            "site_id_SITE_001",
            "region_North",
            "behavior_conservative",
            f"planned_pour_week_{horizon}"
        ]
        for horizon in range(1, 9)
    }

    service.feature_frame = pd.DataFrame(
        [
            {
                "site_id": "SITE_001",
                "week_start": pd.Timestamp(
                    "2024-12-23"
                ),
                "region": "North",
                "behavior": "conservative",
                "year": 2024
            }
        ]
    )

    return service


def test_prediction_returns_eight_weeks():

    service = create_test_service()

    result = service.predict(
        site_id="SITE_001",
        planned_pour_tonnes=[10.0] * 8
    )

    assert (
        result.forecast_origin_week
        == date(2024, 12, 23)
    )

    assert len(result.forecasts) == 8

    assert (
        result.forecasts[0]
        .forecast_week_start
        == date(2024, 12, 30)
    )

    assert (
        result.forecasts[-1]
        .forecast_week_start
        == date(2025, 2, 17)
    )

    assert all(
        forecast.predicted_demand_tonnes
        == 110.0
        for forecast
        in result.forecasts
    )


def test_unknown_site_is_rejected():

    service = create_test_service()

    with pytest.raises(
        ForecastNotFoundError,
        match="Unknown site_id"
    ):

        service.predict(
            site_id="SITE_999",
            planned_pour_tonnes=[10.0] * 8
        )


def test_request_requires_eight_schedule_values():

    with pytest.raises(ValidationError):

        ForecastRequest(
            site_id="SITE_001",
            planned_pour_tonnes=[
                100,
                110,
                120
            ]
        )


def test_negative_planned_pour_is_rejected():

    with pytest.raises(ValidationError):

        ForecastRequest(
            site_id="SITE_001",
            planned_pour_tonnes=[
                100,
                110,
                120,
                130,
                -10,
                150,
                160,
                170
            ]
        )


def test_origin_must_be_monday():

    with pytest.raises(ValidationError):

        ForecastRequest(
            site_id="SITE_001",
            forecast_origin_week=(
                date(2024, 12, 24)
            ),
            planned_pour_tonnes=[
                100
            ] * 8
        )