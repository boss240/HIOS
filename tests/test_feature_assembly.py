from datetime import datetime, timedelta, timezone

import pytest

from app.feature_assembly import FEATURE_SCHEMA_VERSION, PlantGeometry, build_model_001_features
from app.weather_normalization import normalize_weather


def weather_at(valid_at, **changes):
    values = dict(
        provider="fixture", product="forecast", mapping_version="v1",
        provider_issued_at=valid_at - timedelta(hours=2), valid_at=valid_at,
        interval_end=valid_at + timedelta(hours=1), retrieved_at=valid_at - timedelta(hours=1),
        ghi=700, ghi_unit="W/m2", cloud_cover=20, cloud_cover_unit="%",
        temperature=25, temperature_unit="C", dni=600, dhi=100,
    )
    values.update(changes)
    return normalize_weather(**values)


@pytest.fixture
def kyiv_geometry():
    return PlantGeometry(50.45, 30.52, tilt_degrees=30, surface_azimuth_degrees=180)


def test_builds_versioned_poa_features_from_as_issued_weather(kyiv_geometry):
    valid_at = datetime(2026, 6, 21, 9, 0, tzinfo=timezone.utc)
    bundle = build_model_001_features(
        weather=weather_at(valid_at), geometry=kyiv_geometry, forecast_origin_utc=valid_at - timedelta(hours=1),
    )

    assert bundle.feature_schema_version == FEATURE_SCHEMA_VERSION
    assert bundle.interval_midpoint_utc == valid_at + timedelta(minutes=30)
    assert bundle.solar_elevation_degrees > 50
    assert bundle.plane_of_array_irradiance_wm2 > 0
    assert bundle.model_input.cell_temperature_c == 25


def test_night_context_has_zero_poa(kyiv_geometry):
    valid_at = datetime(2026, 6, 21, 0, 0, tzinfo=timezone.utc)
    bundle = build_model_001_features(
        weather=weather_at(valid_at), geometry=kyiv_geometry, forecast_origin_utc=valid_at - timedelta(hours=1),
    )

    assert bundle.solar_elevation_degrees < 0
    assert bundle.plane_of_array_irradiance_wm2 == 0


def test_missing_components_or_future_weather_fail_closed(kyiv_geometry):
    valid_at = datetime(2026, 6, 21, 9, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="DNI and DHI"):
        build_model_001_features(
            weather=weather_at(valid_at, dni=None), geometry=kyiv_geometry,
            forecast_origin_utc=valid_at - timedelta(hours=1),
        )
    with pytest.raises(ValueError, match="not available"):
        build_model_001_features(
            weather=weather_at(valid_at, retrieved_at=valid_at), geometry=kyiv_geometry,
            forecast_origin_utc=valid_at - timedelta(hours=1),
        )


@pytest.mark.parametrize("values", [
    (91, 30, 30, 180),
    (50, 30, 91, 180),
    (50, 30, 30, 180, 1.1),
])
def test_rejects_invalid_geometry(values):
    with pytest.raises(ValueError):
        PlantGeometry(*values)
