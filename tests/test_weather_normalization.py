from datetime import datetime, timedelta, timezone

import pytest

from app.weather_normalization import normalize_weather


ORIGIN = datetime(2026, 9, 6, 10, tzinfo=timezone.utc)


def normalized(**changes):
    values = dict(
        provider="primary-role", product="forecast", mapping_version="v1",
        provider_issued_at=ORIGIN, valid_at=ORIGIN + timedelta(hours=1),
        interval_end=ORIGIN + timedelta(hours=2), retrieved_at=ORIGIN,
        ghi=1100, ghi_unit="W/m2", cloud_cover=40, cloud_cover_unit="%",
        temperature=293.15, temperature_unit="K", wind_speed=36,
        wind_speed_unit="km/h", dni=None, dhi=None, humidity=None, precipitation=None,
    )
    values.update(changes)
    return normalize_weather(**values)


def test_normalizes_units_and_utc_without_clipping_irradiance():
    weather = normalized(valid_at=(ORIGIN + timedelta(hours=1)).astimezone(
        timezone(timedelta(hours=2))))
    assert weather.irradiance_global_wm2 == 1100
    assert weather.temperature_c == pytest.approx(20)
    assert weather.wind_speed_ms == pytest.approx(10)
    assert weather.valid_at_utc == ORIGIN + timedelta(hours=1)


@pytest.mark.parametrize("changes", [
    {"ghi": -1}, {"cloud_cover": 101}, {"temperature_unit": "F"},
    {"wind_speed": 1, "wind_speed_unit": "mph"},
    {"interval_end": ORIGIN}, {"valid_at": datetime(2026, 9, 6, 11)},
    {"provider_issued_at": ORIGIN + timedelta(minutes=1)},
    {"humidity": float("nan")}, {"provider": ""},
])
def test_rejects_unknown_or_invalid_values(changes):
    with pytest.raises(ValueError):
        normalized(**changes)
