from datetime import datetime, timedelta, timezone

import pytest

from app.operational_weather_composition import (
    OperationalWeatherCompositionError,
    compose_operational_weather,
)
from app.weather_provider_response import ProviderWeatherInterval


START = datetime(2026, 9, 10, 10, tzinfo=timezone.utc)
END = START + timedelta(hours=1)


def interval(provider, values, *, start=START, end=END):
    return ProviderWeatherInterval(provider, start, end, values)


def test_composes_exact_google_covariates_and_solcast_irradiance_with_lineage():
    output = compose_operational_weather(
        google=(interval("google_weather", {"cloud_cover_pct": 40, "temperature_c": 20, "wind_speed_ms": 5}),),
        solcast=(interval("solcast", {"irradiance_global_wm2": 500, "irradiance_direct_wm2": 300, "irradiance_diffuse_wm2": 200, "temperature_c": 22}),),
    )

    assert output[0].irradiance_global_wm2 == 500
    assert output[0].temperature_c == 20
    assert ("temperature_c", "google_weather") in output[0].field_providers
    assert ("irradiance_direct_wm2", "solcast") in output[0].field_providers


def test_rejects_mismatched_or_duplicate_intervals_without_gap_filling():
    google = (interval("google_weather", {"cloud_cover_pct": 40, "temperature_c": 20, "wind_speed_ms": 5}),)
    solcast = (interval("solcast", {"irradiance_global_wm2": 500, "irradiance_direct_wm2": 300, "irradiance_diffuse_wm2": 200}, start=END, end=END + timedelta(hours=1)),)
    with pytest.raises(OperationalWeatherCompositionError, match="match exactly"):
        compose_operational_weather(google=google, solcast=solcast)
    with pytest.raises(OperationalWeatherCompositionError, match="duplicate"):
        compose_operational_weather(google=(google[0], google[0]), solcast=(interval("solcast", {"irradiance_global_wm2": 500, "irradiance_direct_wm2": 300, "irradiance_diffuse_wm2": 200}),))


@pytest.mark.parametrize("google_values,solcast_values", [
    ({"temperature_c": 20, "wind_speed_ms": 5}, {"irradiance_global_wm2": 1, "irradiance_direct_wm2": 1, "irradiance_diffuse_wm2": 1}),
    ({"cloud_cover_pct": 20, "temperature_c": 20, "wind_speed_ms": 5}, {"irradiance_global_wm2": 1, "irradiance_direct_wm2": 1}),
])
def test_rejects_incomplete_field_coverage(google_values, solcast_values):
    with pytest.raises(OperationalWeatherCompositionError):
        compose_operational_weather(
            google=(interval("google_weather", google_values),),
            solcast=(interval("solcast", solcast_values),),
        )
