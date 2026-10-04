from datetime import datetime, timezone

import pytest

from app.weather_provider_response import (
    WeatherProviderSchemaError,
    parse_google_hourly_forecast,
    parse_open_meteo_hourly_benchmark,
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


def open_meteo_payload(**changes):
    payload = {
        "utc_offset_seconds": 0,
        "hourly_units": {
            "time": "iso8601", "temperature_2m": "°C", "cloud_cover": "%",
            "wind_speed_10m": "km/h", "shortwave_radiation": "W/m²",
            "direct_radiation": "W/m²", "diffuse_radiation": "W/m²",
        },
        "hourly": {
            "time": ["2026-09-10T11:00"], "temperature_2m": [20],
            "cloud_cover": [40], "wind_speed_10m": [18],
            "shortwave_radiation": [500], "direct_radiation": [300],
            "diffuse_radiation": [200],
        },
    }
    payload.update(changes)
    return payload


def test_parses_open_meteo_utc_hourly_benchmark_with_preceding_hour_semantics():
    records = parse_open_meteo_hourly_benchmark(open_meteo_payload())
    assert records[0].provider == "open_meteo"
    assert records[0].valid_at_utc == datetime(2026, 9, 10, 10, tzinfo=timezone.utc)
    assert records[0].interval_end_utc == datetime(2026, 9, 10, 11, tzinfo=timezone.utc)
    assert records[0].values == {
        "temperature_c": 20.0, "cloud_cover_pct": 40.0, "wind_speed_ms": 5.0,
        "irradiance_global_wm2": 500.0, "irradiance_direct_wm2": 300.0,
        "irradiance_diffuse_wm2": 200.0,
    }


@pytest.mark.parametrize("payload", [
    open_meteo_payload(utc_offset_seconds=3600),
    open_meteo_payload(hourly_units={}),
    open_meteo_payload(hourly={"time": ["2026-09-10T11:00"]}),
    open_meteo_payload(hourly={
        "time": ["2026-09-10T11:00"], "temperature_2m": [20, 21],
        "cloud_cover": [40], "wind_speed_10m": [18], "shortwave_radiation": [500],
        "direct_radiation": [300], "diffuse_radiation": [200],
    }),
])
def test_rejects_open_meteo_non_utc_or_incomplete_shapes(payload):
    with pytest.raises(WeatherProviderSchemaError):
        parse_open_meteo_hourly_benchmark(payload)
