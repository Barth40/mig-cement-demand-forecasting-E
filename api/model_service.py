import os
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from api.schemas import (
    ForecastResponse,
    SiteInfo,
    WeeklyForecast
)


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "schedule_informed_rf_8week.joblib"
)

DEFAULT_FEATURE_PATH = (
    PROJECT_ROOT
    / "models"
    / "schedule_informed_rf_features.joblib"
)

DEFAULT_DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "cement_operations_merged.csv"
)


# ---------------------------------------------------------
# Features used by the forecasting workflow
# ---------------------------------------------------------

HISTORICAL_FEATURES = [
    "consumption_lag_1",
    "consumption_lag_2",
    "consumption_lag_4",
    "consumption_lag_8",
    "consumption_lag_13",
    "consumption_lag_26",
    "consumption_lag_52",
    "consumption_rolling_mean_4",
    "consumption_rolling_mean_8",
    "consumption_rolling_mean_13",
    "consumption_rolling_mean_26",
    "consumption_rolling_std_8",
    "consumption_rolling_std_26",
    "demand_trend_4_13",
    "demand_trend_8_26"
]


OPERATIONAL_FEATURES = [
    "planned_pour_lag_1",
    "planned_pour_lag_4",
    "deliveries_lag_1",
    "deliveries_lag_4",
    "rain_lag_1",
    "temperature_lag_1",
    "rain_rolling_mean_4",
    "temperature_rolling_mean_4"
]


class ForecastNotFoundError(ValueError):
    """Raised when a site or forecast origin cannot be found."""


class ForecastService:

    def __init__(
        self,
        model_path=None,
        feature_path=None,
        data_path=None
    ):

        self.model_path = Path(
            model_path
            or os.getenv(
                "MODEL_PATH",
                str(DEFAULT_MODEL_PATH)
            )
        )

        self.feature_path = Path(
            feature_path
            or os.getenv(
                "FEATURE_PATH",
                str(DEFAULT_FEATURE_PATH)
            )
        )

        self.data_path = Path(
            data_path
            or os.getenv(
                "DATA_PATH",
                str(DEFAULT_DATA_PATH)
            )
        )

        self.models = {}
        self.features_by_horizon = {}
        self.feature_frame = pd.DataFrame()
        self.source_data_through = None


    @property
    def loaded(self):
        return (
            bool(self.models)
            and not self.feature_frame.empty
        )


    # -----------------------------------------------------
    # Load models and source data
    # -----------------------------------------------------

    def load(self):

        required_paths = [
            self.model_path,
            self.feature_path,
            self.data_path
        ]

        missing_paths = [
            str(path)
            for path in required_paths
            if not path.is_file()
        ]

        if missing_paths:
            raise FileNotFoundError(
                "Required API files are missing: "
                f"{missing_paths}"
            )

        loaded_models = joblib.load(
            self.model_path
        )

        loaded_features = joblib.load(
            self.feature_path
        )

        self.models = {
            int(horizon): model
            for horizon, model
            in loaded_models.items()
        }

        self.features_by_horizon = {
            int(horizon): list(features)
            for horizon, features
            in loaded_features.items()
        }

        expected_horizons = set(
            range(1, 9)
        )

        if set(self.models) != expected_horizons:
            raise ValueError(
                "The model file must contain "
                "horizons 1 through 8."
            )

        if (
            set(self.features_by_horizon)
            != expected_horizons
        ):
            raise ValueError(
                "The feature file must contain "
                "horizons 1 through 8."
            )

        daily_data = pd.read_csv(
            self.data_path,
            parse_dates=["date"]
        )

        self.source_data_through = (
            daily_data["date"]
            .max()
            .date()
        )

        self.feature_frame = (
            self._build_weekly_features(
                daily_data
            )
        )


    # -----------------------------------------------------
    # Recreate weekly model features
    # -----------------------------------------------------

    @staticmethod
    def _build_weekly_features(
        daily_data
    ):

        required_columns = {
            "date",
            "site_id",
            "cement_type",
            "consumed_tonnes",
            "planned_pour_tonnes",
            "opening_inventory_tonnes",
            "deliveries_tonnes",
            "closing_inventory_tonnes",
            "rain_mm",
            "avg_temp_c",
            "silo_capacity",
            "region",
            "behavior"
        }

        missing_columns = sorted(
            required_columns.difference(
                daily_data.columns
            )
        )

        if missing_columns:
            raise ValueError(
                "Forecast source data is "
                "missing columns: "
                f"{missing_columns}"
            )

        data = (
            daily_data
            .sort_values(
                [
                    "site_id",
                    "date",
                    "cement_type"
                ]
            )
            .reset_index(drop=True)
        )

        data["week_start"] = (
            data["date"]
            - pd.to_timedelta(
                data["date"].dt.dayofweek,
                unit="D"
            )
        )

        weekly_data = (
            data
            .groupby(
                [
                    "site_id",
                    "week_start"
                ],
                as_index=False
            )
            .agg(
                weekly_consumed_tonnes=(
                    "consumed_tonnes",
                    "sum"
                ),
                weekly_planned_pour_tonnes=(
                    "planned_pour_tonnes",
                    "sum"
                ),
                weekly_deliveries_tonnes=(
                    "deliveries_tonnes",
                    "sum"
                ),
                weekly_rain_mm=(
                    "rain_mm",
                    "sum"
                ),
                weekly_avg_temp_c=(
                    "avg_temp_c",
                    "mean"
                ),
                opening_inventory_tonnes=(
                    "opening_inventory_tonnes",
                    "first"
                ),
                closing_inventory_tonnes=(
                    "closing_inventory_tonnes",
                    "last"
                ),
                silo_capacity=(
                    "silo_capacity",
                    "max"
                ),
                region=(
                    "region",
                    "first"
                ),
                behavior=(
                    "behavior",
                    "first"
                )
            )
            .sort_values(
                [
                    "site_id",
                    "week_start"
                ]
            )
            .reset_index(drop=True)
        )


        # -------------------------------------------------
        # Calendar features
        # -------------------------------------------------

        weekly_data["year"] = (
            weekly_data["week_start"]
            .dt.year
        )

        weekly_data["month"] = (
            weekly_data["week_start"]
            .dt.month
        )

        weekly_data["quarter"] = (
            weekly_data["week_start"]
            .dt.quarter
        )

        weekly_data["week_of_year"] = (
            weekly_data["week_start"]
            .dt
            .isocalendar()
            .week
            .astype("int16")
        )

        weekly_data["week_sin"] = np.sin(
            2
            * np.pi
            * weekly_data["week_of_year"]
            / 52
        )

        weekly_data["week_cos"] = np.cos(
            2
            * np.pi
            * weekly_data["week_of_year"]
            / 52
        )


        # -------------------------------------------------
        # Consumption lag features
        # -------------------------------------------------

        consumption_group = (
            weekly_data
            .groupby(
                "site_id",
                sort=False
            )["weekly_consumed_tonnes"]
        )

        for lag in [
            1,
            2,
            4,
            8,
            13,
            26,
            52
        ]:
            weekly_data[
                f"consumption_lag_{lag}"
            ] = (
                consumption_group
                .shift(lag)
            )


        # -------------------------------------------------
        # Consumption rolling features
        # -------------------------------------------------

        historical_consumption = (
            consumption_group.shift(1)
        )

        for window in [
            4,
            8,
            13,
            26
        ]:
            weekly_data[
                f"consumption_rolling_mean_{window}"
            ] = (
                historical_consumption
                .groupby(
                    weekly_data["site_id"]
                )
                .transform(
                    lambda values,
                    current_window=window:
                    values.rolling(
                        current_window,
                        min_periods=current_window
                    ).mean()
                )
            )

        for window in [
            8,
            26
        ]:
            weekly_data[
                f"consumption_rolling_std_{window}"
            ] = (
                historical_consumption
                .groupby(
                    weekly_data["site_id"]
                )
                .transform(
                    lambda values,
                    current_window=window:
                    values.rolling(
                        current_window,
                        min_periods=current_window
                    ).std()
                )
            )


        # -------------------------------------------------
        # Demand trend features
        # -------------------------------------------------

        weekly_data[
            "demand_trend_4_13"
        ] = (
            weekly_data[
                "consumption_rolling_mean_4"
            ]
            -
            weekly_data[
                "consumption_rolling_mean_13"
            ]
        )

        weekly_data[
            "demand_trend_8_26"
        ] = (
            weekly_data[
                "consumption_rolling_mean_8"
            ]
            -
            weekly_data[
                "consumption_rolling_mean_26"
            ]
        )


        # -------------------------------------------------
        # Operational and weather features
        # -------------------------------------------------

        planned_pour_group = (
            weekly_data
            .groupby(
                "site_id",
                sort=False
            )["weekly_planned_pour_tonnes"]
        )

        deliveries_group = (
            weekly_data
            .groupby(
                "site_id",
                sort=False
            )["weekly_deliveries_tonnes"]
        )

        rain_group = (
            weekly_data
            .groupby(
                "site_id",
                sort=False
            )["weekly_rain_mm"]
        )

        temperature_group = (
            weekly_data
            .groupby(
                "site_id",
                sort=False
            )["weekly_avg_temp_c"]
        )

        weekly_data[
            "planned_pour_lag_1"
        ] = planned_pour_group.shift(1)

        weekly_data[
            "planned_pour_lag_4"
        ] = planned_pour_group.shift(4)

        weekly_data[
            "deliveries_lag_1"
        ] = deliveries_group.shift(1)

        weekly_data[
            "deliveries_lag_4"
        ] = deliveries_group.shift(4)

        weekly_data[
            "rain_lag_1"
        ] = rain_group.shift(1)

        weekly_data[
            "temperature_lag_1"
        ] = temperature_group.shift(1)

        weekly_data[
            "rain_rolling_mean_4"
        ] = (
            rain_group
            .shift(1)
            .groupby(
                weekly_data["site_id"]
            )
            .transform(
                lambda values:
                values.rolling(
                    4,
                    min_periods=4
                ).mean()
            )
        )

        weekly_data[
            "temperature_rolling_mean_4"
        ] = (
            temperature_group
            .shift(1)
            .groupby(
                weekly_data["site_id"]
            )
            .transform(
                lambda values:
                values.rolling(
                    4,
                    min_periods=4
                ).mean()
            )
        )


        # Keep rows with sufficient historical data.
        complete_features = (
            HISTORICAL_FEATURES
            + OPERATIONAL_FEATURES
        )

        model_data = (
            weekly_data
            .dropna(
                subset=complete_features
            )
            .reset_index(drop=True)
        )

        return model_data


    # -----------------------------------------------------
    # Return available sites
    # -----------------------------------------------------

    def list_sites(self):

        latest_sites = (
            self.feature_frame
            .sort_values("week_start")
            .groupby(
                "site_id",
                as_index=False
            )
            .tail(1)
            .sort_values("site_id")
        )

        return [
            SiteInfo(
                site_id=row.site_id,
                region=row.region,
                behavior=row.behavior,
                latest_forecast_origin_week=(
                    row.week_start.date()
                )
            )
            for row
            in latest_sites.itertuples(
                index=False
            )
        ]


    # -----------------------------------------------------
    # Generate eight-week forecast
    # -----------------------------------------------------

    def predict(
        self,
        site_id,
        planned_pour_tonnes,
        forecast_origin_week=None
    ):

        site_data = (
            self.feature_frame.loc[
                self.feature_frame[
                    "site_id"
                ]
                == site_id
            ]
        )

        if site_data.empty:
            raise ForecastNotFoundError(
                f"Unknown site_id: {site_id}"
            )

        if forecast_origin_week is None:
            selected_row = (
                site_data
                .sort_values("week_start")
                .iloc[-1]
            )

        else:
            requested_origin = pd.Timestamp(
                forecast_origin_week
            )

            matching_rows = (
                site_data.loc[
                    site_data["week_start"]
                    == requested_origin
                ]
            )

            if matching_rows.empty:

                first_origin = (
                    site_data["week_start"]
                    .min()
                    .date()
                )

                last_origin = (
                    site_data["week_start"]
                    .max()
                    .date()
                )

                raise ForecastNotFoundError(
                    "No usable forecast origin for "
                    f"{site_id} on "
                    f"{forecast_origin_week}. "
                    "Available range is "
                    f"{first_origin} to "
                    f"{last_origin}."
                )

            selected_row = (
                matching_rows.iloc[-1]
            )


        origin_timestamp = pd.Timestamp(
            selected_row["week_start"]
        )

        forecasts = []


        for horizon, planned_pour in enumerate(
            planned_pour_tonnes,
            start=1
        ):

            model_features = (
                self.features_by_horizon[
                    horizon
                ]
            )

            feature_values = {
                feature: 0.0
                for feature
                in model_features
            }

            for feature in model_features:

                if (
                    feature
                    in selected_row.index
                    and pd.notna(
                        selected_row[feature]
                    )
                ):
                    feature_values[feature] = (
                        float(
                            selected_row[
                                feature
                            ]
                        )
                    )


            # Set categorical one-hot variables.
            site_feature = (
                f"site_id_"
                f"{selected_row['site_id']}"
            )

            region_feature = (
                f"region_"
                f"{selected_row['region']}"
            )

            behavior_feature = (
                f"behavior_"
                f"{selected_row['behavior']}"
            )

            if site_feature in feature_values:
                feature_values[
                    site_feature
                ] = 1.0

            if region_feature in feature_values:
                feature_values[
                    region_feature
                ] = 1.0

            if behavior_feature in feature_values:
                feature_values[
                    behavior_feature
                ] = 1.0


            schedule_feature = (
                f"planned_pour_week_"
                f"{horizon}"
            )

            feature_values[
                schedule_feature
            ] = float(planned_pour)


            model_input = pd.DataFrame(
                [feature_values],
                columns=model_features
            )

            prediction = (
                self.models[horizon]
                .predict(model_input)[0]
            )

            prediction = max(
                float(prediction),
                0.0
            )

            forecast_date = (
                origin_timestamp
                + pd.Timedelta(
                    weeks=horizon
                )
            ).date()

            forecasts.append(
                WeeklyForecast(
                    horizon_week=horizon,
                    forecast_week_start=(
                        forecast_date
                    ),
                    planned_pour_tonnes=round(
                        float(planned_pour),
                        2
                    ),
                    predicted_demand_tonnes=round(
                        prediction,
                        2
                    )
                )
            )


        return ForecastResponse(
            site_id=site_id,
            forecast_origin_week=(
                origin_timestamp.date()
            ),
            forecasts=forecasts
        )