"""Pure, schema-strict weather response parsing for approved provider roles.

No credentials, HTTP client, retry loop or persistence belongs in this module.
Parsed records retain provider-specific field coverage so callers cannot pretend
that Google supplies irradiance or that Solcast supplies cloud cover.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
import re
from typing import Any, Mapping


class WeatherProviderSchemaError(ValueError):
    """A provider response omitted or changed a required documented field."""


@dataclass(frozen=True)
class ProviderWeatherInterval:
    provider: str
    valid_at_utc: datetime
    interval_end_utc: datetime
    values: Mapping[str, float]


def _timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise WeatherProviderSchemaError(f"{name} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise WeatherProviderSchemaError(f"{name} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise WeatherProviderSchemaError(f"{name} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _number(value: Any, name: str, *, minimum: float = 0,
            maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise WeatherProviderSchemaError(f"{name} must be a finite number")
    result = float(value)
    if result < minimum:
        raise WeatherProviderSchemaError(f"{name} must be at least {minimum}")
    if maximum is not None and result > maximum:
        raise WeatherProviderSchemaError(f"{name} must be at most {maximum}")
    return result


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise WeatherProviderSchemaError(f"{name} must be an object")
    return value


def parse_google_hourly_forecast(payload: Mapping[str, Any]) -> tuple[ProviderWeatherInterval, ...]:
    """Parse documented Google forecastHours using the enforced metric request."""
    hours = payload.get("forecastHours")
    if not isinstance(hours, list) or not hours:
        raise WeatherProviderSchemaError("forecastHours must be a non-empty list")
    records = []
    for index, raw in enumerate(hours):
        item = _mapping(raw, f"forecastHours[{index}]")
        interval = _mapping(item.get("interval"), "interval")
        valid_at = _timestamp(interval.get("startTime"), "interval.startTime")
        interval_end = _timestamp(interval.get("endTime"), "interval.endTime")
        if interval_end <= valid_at:
            raise WeatherProviderSchemaError("interval.endTime must follow interval.startTime")
        temperature = _mapping(item.get("temperature"), "temperature")
        if temperature.get("unit") != "CELSIUS":
            raise WeatherProviderSchemaError("Google temperature unit must be CELSIUS")
        wind = _mapping(item.get("wind"), "wind")
        speed = _mapping(wind.get("speed"), "wind.speed")
        if speed.get("unit") != "KILOMETERS_PER_HOUR":
            raise WeatherProviderSchemaError("Google wind speed unit must be KILOMETERS_PER_HOUR")
        records.append(ProviderWeatherInterval(
            provider="google_weather", valid_at_utc=valid_at, interval_end_utc=interval_end,
            values={
                "temperature_c": _number(temperature.get("degrees"), "temperature.degrees", minimum=-100),
                "cloud_cover_pct": _number(item.get("cloudCover"), "cloudCover", minimum=0, maximum=100),
                "wind_speed_ms": _number(speed.get("value"), "wind.speed.value") / 3.6,
            },
        ))
    return tuple(records)


_PERIOD = re.compile(r"^PT(?:(\d+)H)?(?:(\d+)M)?$")


def _period(value: Any) -> timedelta:
    if not isinstance(value, str):
        raise WeatherProviderSchemaError("period must be an ISO-8601 duration")
    match = _PERIOD.fullmatch(value)
    if not match:
        raise WeatherProviderSchemaError("period must be an ISO-8601 duration")
    duration = timedelta(hours=int(match.group(1) or 0), minutes=int(match.group(2) or 0))
    if duration <= timedelta(0):
        raise WeatherProviderSchemaError("period must be positive")
    return duration


def parse_solcast_radiation_forecast(payload: Mapping[str, Any]) -> tuple[ProviderWeatherInterval, ...]:
    """Parse Solcast radiation-and-weather rows with explicit interval semantics."""
    forecasts = payload.get("forecasts")
    if not isinstance(forecasts, list) or not forecasts:
        raise WeatherProviderSchemaError("forecasts must be a non-empty list")
    records = []
    for index, raw in enumerate(forecasts):
        item = _mapping(raw, f"forecasts[{index}]")
        interval_end = _timestamp(item.get("period_end"), "period_end")
        valid_at = interval_end - _period(item.get("period"))
        records.append(ProviderWeatherInterval(
            provider="solcast", valid_at_utc=valid_at, interval_end_utc=interval_end,
            values={
                "irradiance_global_wm2": _number(item.get("ghi"), "ghi"),
                "irradiance_direct_wm2": _number(item.get("dni"), "dni"),
                "irradiance_diffuse_wm2": _number(item.get("dhi"), "dhi"),
                "temperature_c": _number(item.get("air_temp"), "air_temp", minimum=-100),
                "wind_speed_ms": _number(item.get("wind_speed_10m"), "wind_speed_10m"),
            },
        ))
    return tuple(records)
