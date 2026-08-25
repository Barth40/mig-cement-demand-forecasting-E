import os

import plotly.graph_objects as go
import requests

from dash import (
    ALL,
    Dash,
    Input,
    Output,
    State,
    dash_table,
    dcc,
    html
)


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8000"
)

DASHBOARD_HOST = os.getenv(
    "DASHBOARD_HOST",
    "127.0.0.1"
)

DASHBOARD_PORT = int(
    os.getenv(
        "DASHBOARD_PORT",
        "8050"
    )
)


# ---------------------------------------------------------
# Application
# ---------------------------------------------------------

app = Dash(
    __name__,
    title="MIG Cement Demand Dashboard"
)

server = app.server


# ---------------------------------------------------------
# Reusable styles
# ---------------------------------------------------------

PAGE_STYLE = {
    "backgroundColor": "#f4f7fb",
    "minHeight": "100vh",
    "padding": "24px",
    "fontFamily": "Arial, sans-serif",
    "color": "#1f2937"
}

CARD_STYLE = {
    "backgroundColor": "white",
    "borderRadius": "10px",
    "padding": "20px",
    "boxShadow": (
        "0 2px 8px rgba(0, 0, 0, 0.08)"
    )
}

INPUT_STYLE = {
    "width": "100%",
    "padding": "9px",
    "border": "1px solid #cbd5e1",
    "borderRadius": "6px"
}


# ---------------------------------------------------------
# Planned-pour input controls
# ---------------------------------------------------------

planned_pour_inputs = []

for week in range(1, 9):

    planned_pour_inputs.append(
        html.Div(
            [
                html.Label(
                    f"Week {week}",
                    style={
                        "display": "block",
                        "fontWeight": "600",
                        "marginBottom": "6px"
                    }
                ),

                dcc.Input(
                    id={
                        "type": "planned-pour",
                        "index": week
                    },
                    type="number",
                    min=0,
                    step=0.01,
                    value=150,
                    style=INPUT_STYLE
                )
            ]
        )
    )


# ---------------------------------------------------------
# Dashboard layout
# ---------------------------------------------------------

app.layout = html.Div(
    style=PAGE_STYLE,
    children=[
        dcc.Interval(
            id="initial-api-check",
            interval=500,
            max_intervals=1
        ),

        html.Div(
            [
                html.Div(
                    [
                        html.H1(
                            "MIG Cement Demand Forecast",
                            style={
                                "margin": "0",
                                "color": "#0f172a"
                            }
                        ),

                        html.P(
                            "Schedule-informed eight-week "
                            "cement demand planning",
                            style={
                                "marginBottom": "0",
                                "color": "#64748b"
                            }
                        )
                    ]
                ),

                html.Div(
                    id="api-status",
                    children="Checking API...",
                    style={
                        "padding": "8px 14px",
                        "borderRadius": "20px",
                        "backgroundColor": "#fef3c7",
                        "color": "#92400e",
                        "fontWeight": "600"
                    }
                )
            ],
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "marginBottom": "24px"
            }
        ),

        html.Div(
            [
                html.Div(
                    [
                        html.H3(
                            "Forecast configuration",
                            style={"marginTop": "0"}
                        ),

                        html.Label(
                            "Construction site",
                            style={
                                "display": "block",
                                "fontWeight": "600",
                                "marginBottom": "6px"
                            }
                        ),

                        dcc.Dropdown(
                            id="site-selector",
                            placeholder="Select a site",
                            clearable=False
                        ),

                        html.Label(
                            "Forecast-origin week (optional)",
                            style={
                                "display": "block",
                                "fontWeight": "600",
                                "marginTop": "18px",
                                "marginBottom": "6px"
                            }
                        ),

                        dcc.DatePickerSingle(
                            id="forecast-origin",
                            placeholder="Use latest available week",
                            display_format="DD MMM YYYY",
                            clearable=True,
                            style={
                                "width": "100%"
                            }
                        ),

                        html.H4(
                            "Planned pour tonnes",
                            style={
                                "marginTop": "24px",
                                "marginBottom": "12px"
                            }
                        ),

                        html.Div(
                            planned_pour_inputs,
                            style={
                                "display": "grid",
                                "gridTemplateColumns": (
                                    "repeat(2, minmax(0, 1fr))"
                                ),
                                "gap": "12px"
                            }
                        ),

                        html.Button(
                            "Generate Forecast",
                            id="forecast-button",
                            n_clicks=0,
                            style={
                                "width": "100%",
                                "marginTop": "24px",
                                "padding": "12px",
                                "border": "none",
                                "borderRadius": "7px",
                                "backgroundColor": "#2563eb",
                                "color": "white",
                                "fontWeight": "700",
                                "cursor": "pointer"
                            }
                        ),

                        html.Div(
                            id="forecast-error",
                            style={
                                "marginTop": "14px",
                                "color": "#b91c1c",
                                "fontWeight": "600"
                            }
                        )
                    ],
                    style=CARD_STYLE
                ),

                html.Div(
                    [
                        html.Div(
                            id="forecast-summary",
                            style={
                                "display": "grid",
                                "gridTemplateColumns": (
                                    "repeat(3, minmax(0, 1fr))"
                                ),
                                "gap": "12px",
                                "marginBottom": "18px"
                            }
                        ),

                        dcc.Graph(
                            id="forecast-chart",
                            figure=go.Figure()
                        )
                    ],
                    style=CARD_STYLE
                )
            ],
            style={
                "display": "grid",
                "gridTemplateColumns": (
                    "340px minmax(0, 1fr)"
                ),
                "gap": "20px",
                "alignItems": "start"
            }
        ),

        html.Div(
            [
                html.H3(
                    "Eight-week forecast details",
                    style={"marginTop": "0"}
                ),

                dash_table.DataTable(
                    id="forecast-table",
                    columns=[
                        {
                            "name": "Week",
                            "id": "horizon_week"
                        },
                        {
                            "name": "Forecast date",
                            "id": "forecast_week_start"
                        },
                        {
                            "name": "Planned pour (t)",
                            "id": "planned_pour_tonnes"
                        },
                        {
                            "name": "Predicted demand (t)",
                            "id": "predicted_demand_tonnes"
                        },
                        {
                            "name": "Difference (t)",
                            "id": "difference_tonnes"
                        },
                        {
                            "name": "Status",
                            "id": "status"
                        }
                    ],
                    data=[],
                    style_table={
                        "overflowX": "auto"
                    },
                    style_header={
                        "backgroundColor": "#e2e8f0",
                        "fontWeight": "700"
                    },
                    style_cell={
                        "padding": "10px",
                        "textAlign": "center",
                        "border": "1px solid #e2e8f0"
                    },
                    style_data_conditional=[
                        {
                            "if": {
                                "filter_query": (
                                    '{status} = "Potential shortage"'
                                )
                            },
                            "backgroundColor": "#fee2e2",
                            "color": "#991b1b"
                        },
                        {
                            "if": {
                                "filter_query": (
                                    '{status} = "Schedule sufficient"'
                                )
                            },
                            "backgroundColor": "#dcfce7",
                            "color": "#166534"
                        }
                    ]
                )
            ],
            style={
                **CARD_STYLE,
                "marginTop": "20px"
            }
        )
    ]
)


# ---------------------------------------------------------
# Load supported sites and API status
# ---------------------------------------------------------

@app.callback(
    Output(
        "site-selector",
        "options"
    ),
    Output(
        "site-selector",
        "value"
    ),
    Output(
        "api-status",
        "children"
    ),
    Output(
        "api-status",
        "style"
    ),
    Input(
        "initial-api-check",
        "n_intervals"
    )
)
def load_api_information(
    _n_intervals
):

    try:
        health_response = requests.get(
            f"{API_BASE_URL}/health",
            timeout=10
        )

        sites_response = requests.get(
            f"{API_BASE_URL}/sites",
            timeout=10
        )

        health_response.raise_for_status()
        sites_response.raise_for_status()

        health_data = (
            health_response.json()
        )

        sites_data = (
            sites_response.json()
        )

        options = [
            {
                "label": (
                    f"{site['site_id']} — "
                    f"{site['region']} / "
                    f"{site['behavior']}"
                ),
                "value": site["site_id"]
            }
            for site in sites_data
        ]

        default_site = (
            options[0]["value"]
            if options
            else None
        )

        status_text = (
            "API online · "
            f"{health_data['number_of_sites']} sites"
        )

        status_style = {
            "padding": "8px 14px",
            "borderRadius": "20px",
            "backgroundColor": "#dcfce7",
            "color": "#166534",
            "fontWeight": "600"
        }

        return (
            options,
            default_site,
            status_text,
            status_style
        )

    except requests.RequestException:

        return (
            [],
            None,
            "API offline",
            {
                "padding": "8px 14px",
                "borderRadius": "20px",
                "backgroundColor": "#fee2e2",
                "color": "#991b1b",
                "fontWeight": "600"
            }
        )


# ---------------------------------------------------------
# Generate forecast
# ---------------------------------------------------------

@app.callback(
    Output(
        "forecast-chart",
        "figure"
    ),
    Output(
        "forecast-table",
        "data"
    ),
    Output(
        "forecast-summary",
        "children"
    ),
    Output(
        "forecast-error",
        "children"
    ),
    Input(
        "forecast-button",
        "n_clicks"
    ),
    State(
        "site-selector",
        "value"
    ),
    State(
        "forecast-origin",
        "date"
    ),
    State(
        {
            "type": "planned-pour",
            "index": ALL
        },
        "value"
    ),
    prevent_initial_call=True
)
def generate_forecast(
    _n_clicks,
    site_id,
    forecast_origin,
    planned_pour_values
):

    empty_figure = go.Figure()

    if not site_id:
        return (
            empty_figure,
            [],
            [],
            "Please select a site."
        )

    if (
        len(planned_pour_values) != 8
        or any(
            value is None
            for value
            in planned_pour_values
        )
    ):
        return (
            empty_figure,
            [],
            [],
            "Enter planned-pour values "
            "for all eight weeks."
        )

    request_body = {
        "site_id": site_id,
        "planned_pour_tonnes": (
            planned_pour_values
        )
    }

    if forecast_origin:
        request_body[
            "forecast_origin_week"
        ] = forecast_origin

    try:
        response = requests.post(
            f"{API_BASE_URL}/forecast",
            json=request_body,
            timeout=120
        )

        if response.status_code == 422:
            error_data = response.json()

            return (
                empty_figure,
                [],
                [],
                "Invalid request. Forecast origin "
                "must be a Monday and all planned "
                "pour values must be non-negative."
            )

        if response.status_code == 404:
            error_message = (
                response.json()
                .get(
                    "detail",
                    "Forecast origin was not found."
                )
            )

            return (
                empty_figure,
                [],
                [],
                error_message
            )

        response.raise_for_status()

        forecast_data = (
            response.json()
        )

    except requests.RequestException as error:

        return (
            empty_figure,
            [],
            [],
            f"Unable to contact FastAPI: {error}"
        )


    forecast_rows = (
        forecast_data["forecasts"]
    )

    chart_weeks = [
        f"Week {row['horizon_week']}"
        for row in forecast_rows
    ]

    planned_values = [
        row["planned_pour_tonnes"]
        for row in forecast_rows
    ]

    predicted_values = [
        row["predicted_demand_tonnes"]
        for row in forecast_rows
    ]


    # -----------------------------------------------------
    # Create comparison chart
    # -----------------------------------------------------

    figure = go.Figure()

    figure.add_trace(
        go.Bar(
            x=chart_weeks,
            y=planned_values,
            name="Planned pour",
            marker_color="#94a3b8"
        )
    )

    figure.add_trace(
        go.Scatter(
            x=chart_weeks,
            y=predicted_values,
            name="Predicted demand",
            mode="lines+markers",
            line={
                "color": "#2563eb",
                "width": 3
            },
            marker={
                "size": 9
            }
        )
    )

    figure.update_layout(
        title=(
            f"Eight-week demand forecast: "
            f"{site_id}"
        ),
        xaxis_title="Forecast horizon",
        yaxis_title="Tonnes",
        template="plotly_white",
        legend={
            "orientation": "h",
            "y": 1.12
        },
        margin={
            "l": 50,
            "r": 30,
            "t": 80,
            "b": 50
        }
    )


    # -----------------------------------------------------
    # Prepare table
    # -----------------------------------------------------

    table_rows = []

    for row in forecast_rows:

        difference = round(
            row["planned_pour_tonnes"]
            - row[
                "predicted_demand_tonnes"
            ],
            2
        )

        status_text = (
            "Schedule sufficient"
            if difference >= 0
            else "Potential shortage"
        )

        table_rows.append(
            {
                **row,
                "difference_tonnes": (
                    difference
                ),
                "status": status_text
            }
        )


    # -----------------------------------------------------
    # Summary cards
    # -----------------------------------------------------

    total_demand = round(
        sum(predicted_values),
        2
    )

    average_demand = round(
        total_demand
        / len(predicted_values),
        2
    )

    maximum_demand = round(
        max(predicted_values),
        2
    )

    summary_cards = [
        create_summary_card(
            "Total predicted demand",
            f"{total_demand:,.2f} t",
            "#2563eb"
        ),
        create_summary_card(
            "Average weekly demand",
            f"{average_demand:,.2f} t",
            "#0f766e"
        ),
        create_summary_card(
            "Peak weekly demand",
            f"{maximum_demand:,.2f} t",
            "#c2410c"
        )
    ]

    return (
        figure,
        table_rows,
        summary_cards,
        ""
    )


# ---------------------------------------------------------
# Summary-card component
# ---------------------------------------------------------

def create_summary_card(
    title,
    value,
    colour
):

    return html.Div(
        [
            html.Div(
                title,
                style={
                    "fontSize": "13px",
                    "color": "#64748b"
                }
            ),

            html.Div(
                value,
                style={
                    "fontSize": "22px",
                    "fontWeight": "700",
                    "color": colour,
                    "marginTop": "6px"
                }
            )
        ],
        style={
            "padding": "14px",
            "border": "1px solid #e2e8f0",
            "borderRadius": "8px",
            "backgroundColor": "#f8fafc"
        }
    )


# ---------------------------------------------------------
# Run dashboard
# ---------------------------------------------------------

if __name__ == "__main__":

    app.run(
        host=DASHBOARD_HOST,
        port=DASHBOARD_PORT,
        debug=False
    )