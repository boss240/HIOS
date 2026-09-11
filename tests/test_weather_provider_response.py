from datetime import datetime, timezone

import pytest

from app.weather_provider_response import (
    WeatherProviderSchemaError,
    parse_google_hourly_forecast,
    parse_solcast_radiation_forecast,
)


def test_parses_google_metric_covariates_without_inventing_irradiance():
    records = parse_google_hourly_forecast({"forecastHours": [{
        "interval": {"startTime": "2026-09-10T10:00:00Z", "endTime": "2026-09-10T11:00:00Z"},
        "temperature": {"degrees": 20, "unit": "CELSIUS"}, "cloudCover": 40,
        "wind": {"speed": {"value": 18, "unit": "KILOMETERS_PER_HOUR"}},
    }]})

    assert records[0].valid_at_utc == datetime(2026, 9, 10, 10, tzinfo=timezone.utc)
    assert records[0].values == {"temperature_c": 20.0, "cloud_cover_pct": 40.0, "wind_speed_ms": 5.0}
    assert "irradiance_global_wm2" not in records[0].values


@pytest.mark.parametrize("payload", [
    {}, {"forecastHours": []}, {"forecastHours": [{"interval": {}}]},
    {"forecastHours": [{"interval": {"startTime": "2026-09-10T10:00:00Z", "endTime": "2026-09-10T11:00:00Z"}, "temperature": {"degrees": 20, "unit": "FAHRENHEIT"}}]},
    {"forecastHours": [{"interval": {"startTime": "2026-09-10T10:00:00Z", "endTime": "2026-09-10T11:00:00Z"}, "temperature": {"degrees": 20, "unit": "CELSIUS"}, "cloudCover": 101, "wind": {"speed": {"value": 1, "unit": "KILOMETERS_PER_HOUR"}}}]},
])
def test_rejects_incomplete_or_non_metric_google_payloads(payload):
    with pytest.raises(WeatherProviderSchemaError):
        parse_google_hourly_forecast(payload)


def test_parses_solcast_irradiance_with_period_end_interval_semantics():
    records = parse_solcast_radiation_forecast({"forecasts": [{
        "period_end": "2026-09-10T11:00:00+00:00", "period": "PT60M",
        "ghi": 500, "dni": 300, "dhi": 200, "air_temp": 21.5, "wind_speed_10m": 4,
    }]})
    assert records[0].valid_at_utc == datetime(2026, 9, 10, 10, tzinfo=timezone.utc)
    assert records[0].values["irradiance_direct_wm2"] == 300


@pytest.mark.parametrize("payload", [
    {}, {"forecasts": []}, {"forecasts": [{"period_end": "2026-09-10T11:00:00Z", "period": "PT0M"}]},
    {"forecasts": [{"period_end": "2026-09-10T11:00:00Z", "period": "PT60M", "ghi": -1, "dni": 1, "dhi": 1, "air_temp": 1, "wind_speed_10m": 1}]},
])
def test_rejects_incomplete_or_invalid_solcast_payloads(payload):
    with pytest.raises(WeatherProviderSchemaError):
        parse_solcast_radiation_forecast(payload)
