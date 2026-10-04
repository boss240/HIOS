"""Pure, schema-strict weather response parsing for approved provider roles.

No credentials, HTTP client, retry loop or persistence belongs in this module.
Parsed records retain provider-specific field coverage so callers cannot pretend
that Google supplies irradiance or that Solcast supplies cloud cover.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
    # Some providers return instantaneous covariates alongside interval means.
    # Keep those values out of interval means and retain their sampling time.
    instant_values: Mapping[str, float] = field(default_factory=dict)
    instant_at_utc: datetime | None = None


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


_OPEN_METEO_FIELDS = (
    "temperature_2m", "cloud_cover", "wind_speed_10m", "shortwave_radiation",
    "direct_normal_irradiance", "diffuse_radiation",
)


def _open_meteo_time(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise WeatherProviderSchemaError("Open-Meteo time must be a non-empty ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise WeatherProviderSchemaError("Open-Meteo time must be ISO-8601") from error
    if parsed.tzinfo is None:
        # The parser accepts naive timestamps only after the response proves UTC.
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def parse_open_meteo_hourly_benchmark(payload: Mapping[str, Any]) -> tuple[ProviderWeatherInterval, ...]:
    """Parse a UTC Open-Meteo hourly solar-weather benchmark response.

    Open-Meteo hourly radiation values represent the preceding-hour mean, so
    every timestamp is treated as the interval end. This parser is for a
    challenger/benchmark path and does not authorize operational failover.
    """
    offset = payload.get("utc_offset_seconds")
    if isinstance(offset, bool) or not isinstance(offset, (int, float)) or offset != 0:
        raise WeatherProviderSchemaError("Open-Meteo response must declare UTC offset zero")
    units = _mapping(payload.get("hourly_units"), "hourly_units")
    hourly = _mapping(payload.get("hourly"), "hourly")
    required_units = {
        "time": "iso8601", "temperature_2m": "°C", "cloud_cover": "%",
        "wind_speed_10m": "km/h", "shortwave_radiation": "W/m²",
        "direct_normal_irradiance": "W/m²", "diffuse_radiation": "W/m²",
    }
    for field, unit in required_units.items():
        if units.get(field) != unit:
            raise WeatherProviderSchemaError(f"Open-Meteo {field} must use {unit}")
    values: dict[str, list[Any]] = {}
    for field in ("time",) + _OPEN_METEO_FIELDS:
        rows = hourly.get(field)
        if not isinstance(rows, list) or not rows:
            raise WeatherProviderSchemaError(f"Open-Meteo hourly.{field} must be a non-empty array")
        values[field] = rows
    count = len(values["time"])
    if any(len(rows) != count for rows in values.values()):
        raise WeatherProviderSchemaError("Open-Meteo hourly arrays must have equal length")
    records = []
    previous_end = None
    for index in range(count):
        interval_end = _open_meteo_time(values["time"][index])
        if interval_end.minute or interval_end.second or interval_end.microsecond:
            raise WeatherProviderSchemaError("Open-Meteo timestamps must align to UTC hours")
        if previous_end is not None and interval_end <= previous_end:
            raise WeatherProviderSchemaError("Open-Meteo timestamps must increase without duplicates")
        previous_end = interval_end
        records.append(ProviderWeatherInterval(
            provider="open_meteo", valid_at_utc=interval_end - timedelta(hours=1),
            interval_end_utc=interval_end, values={
                "irradiance_global_wm2": _number(values["shortwave_radiation"][index], "shortwave_radiation"),
                "irradiance_direct_wm2": _number(values["direct_normal_irradiance"][index], "direct_normal_irradiance"),
                "irradiance_diffuse_wm2": _number(values["diffuse_radiation"][index], "diffuse_radiation"),
            }, instant_at_utc=interval_end, instant_values={
                "temperature_c": _number(values["temperature_2m"][index], "temperature_2m", minimum=-100),
                "cloud_cover_pct": _number(values["cloud_cover"][index], "cloud_cover", minimum=0, maximum=100),
                "wind_speed_ms": _number(values["wind_speed_10m"][index], "wind_speed_10m") / 3.6,
            },
        ))
    return tuple(records)
