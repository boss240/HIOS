import pytest

from app.weather_provider_requests import (
    GOOGLE_HOURLY_FORECAST_PATH,
    SOLCAST_OUTPUT_PARAMETERS,
    SOLCAST_RADIATION_FORECAST_PATH,
    GoogleHourlyForecastRequest,
    SolcastRadiationForecastRequest,
)


def test_google_hourly_request_uses_metric_units_and_documented_horizon_bounds():
    request = GoogleHourlyForecastRequest(50.45, 30.52, hours=48, page_size=24)

    assert GOOGLE_HOURLY_FORECAST_PATH == "/v1/forecast/hours:lookup"
    assert request.query_parameters() == {
        "location.latitude": "50.45", "location.longitude": "30.52",
        "hours": "48", "pageSize": "24", "unitsSystem": "METRIC",
    }


@pytest.mark.parametrize("changes", [
    {"latitude": 91}, {"longitude": -181}, {"hours": 0},
    {"hours": 241}, {"page_size": 25}, {"page_token": " "},
])
def test_google_request_rejects_invalid_location_horizon_or_pagination(changes):
    values = {"latitude": 50, "longitude": 30, "hours": 24}
    values.update(changes)
    with pytest.raises(ValueError):
        GoogleHourlyForecastRequest(**values)


def test_solcast_request_limits_fields_to_model_required_irradiance_and_covariates():
    request = SolcastRadiationForecastRequest(50.45, 30.52)

    assert SOLCAST_RADIATION_FORECAST_PATH == "/data/forecast/radiation_and_weather"
    assert request.query_parameters()["output_parameters"] == SOLCAST_OUTPUT_PARAMETERS
    assert "api_key" not in request.query_parameters()


@pytest.mark.parametrize("latitude,longitude", [(91, 0), (0, 181), (True, 30), (float("nan"), 30)])
def test_solcast_request_rejects_invalid_coordinates(latitude, longitude):
    with pytest.raises(ValueError):
        SolcastRadiationForecastRequest(latitude, longitude)
