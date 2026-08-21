from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    HTTPException,
    Request
)

from api.model_service import (
    ForecastNotFoundError,
    ForecastService
)

from api.schemas import (
    ForecastRequest,
    ForecastResponse,
    HealthResponse,
    SiteInfo
)


# ---------------------------------------------------------
# Load the model once when FastAPI starts
# ---------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):

    forecast_service = ForecastService()

    forecast_service.load()

    app.state.forecast_service = (
        forecast_service
    )

    yield


# ---------------------------------------------------------
# Create FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title="MIG Cement Demand Forecast API",
    version="1.0.0",
    description=(
        "Schedule-informed cement demand "
        "forecasting for Weeks 1 through 8."
    ),
    lifespan=lifespan
)


# ---------------------------------------------------------
# Retrieve the loaded forecasting service
# ---------------------------------------------------------

def get_forecast_service(
    request: Request
) -> ForecastService:

    return (
        request
        .app
        .state
        .forecast_service
    )


# ---------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------

@app.get(
    "/",
    tags=["Service"]
)
def root():

    return {
        "service": (
            "MIG Cement Demand Forecast API"
        ),
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health",
        "sites": "/sites"
    }


# ---------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Service"]
)
def health(
    request: Request
):

    service = get_forecast_service(
        request
    )

    return HealthResponse(
        status=(
            "ok"
            if service.loaded
            else "not_ready"
        ),
        model_loaded=service.loaded,
        horizons=sorted(
            service.models
        ),
        number_of_sites=(
            service
            .feature_frame["site_id"]
            .nunique()
        ),
        source_data_through=(
            service.source_data_through
        )
    )


# ---------------------------------------------------------
# Supported sites endpoint
# ---------------------------------------------------------

@app.get(
    "/sites",
    response_model=list[SiteInfo],
    tags=["Forecast"]
)
def sites(
    request: Request
):

    service = get_forecast_service(
        request
    )

    return service.list_sites()


# ---------------------------------------------------------
# Forecast endpoint
# ---------------------------------------------------------

@app.post(
    "/forecast",
    response_model=ForecastResponse,
    tags=["Forecast"]
)
def forecast(
    payload: ForecastRequest,
    request: Request
):

    service = get_forecast_service(
        request
    )

    try:

        return service.predict(
            site_id=payload.site_id,
            planned_pour_tonnes=(
                payload.planned_pour_tonnes
            ),
            forecast_origin_week=(
                payload.forecast_origin_week
            )
        )

    except ForecastNotFoundError as error:

        raise HTTPException(
            status_code=404,
            detail=str(error)
        ) from error