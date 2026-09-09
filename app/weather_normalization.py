"""Canonical weather interval validation for Sprint 2 provider adapters."""
from dataclasses import dataclass
from datetime import datetime, timezone
import math


@dataclass(frozen=True)
class NormalizedWeather:
    provider: str
    product: str
    mapping_version: str
    provider_issued_at_utc: datetime
    valid_at_utc: datetime
    interval_end_utc: datetime
    retrieved_at_utc: datetime
    irradiance_global_wm2: float
    cloud_cover_pct: float
    temperature_c: float
    wind_speed_ms: float | None = None
    irradiance_direct_wm2: float | None = None
    irradiance_diffuse_wm2: float | None = None
    relative_humidity_pct: float | None = None
    precipitation_mm: float | None = None


def _utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _number(value, name: str, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    if maximum is not None and result > maximum:
        raise ValueError(f"{name} must be at most {maximum}")
    return result


def _name(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def normalize_weather(*, provider: str, product: str, mapping_version: str,
                      provider_issued_at: datetime, valid_at: datetime,
                      interval_end: datetime, retrieved_at: datetime,
                      ghi: float, ghi_unit: str, cloud_cover: float,
                      cloud_cover_unit: str, temperature: float,
                      temperature_unit: str, wind_speed: float | None = None,
                      wind_speed_unit: str | None = None, dni: float | None = None,
                      dhi: float | None = None, humidity: float | None = None,
                      precipitation: float | None = None) -> NormalizedWeather:
    """Validate and convert one provider interval without guessing missing values.

    Provider adapters supply their documented mapping. GHI may exceed 1000 W/m²;
    only impossible negative values are rejected. The returned timestamps are UTC,
    and the interval remains exactly as supplied rather than being resampled.
    """
    provider_issued_at_utc = _utc(provider_issued_at, "provider_issued_at")
    retrieved_at_utc = _utc(retrieved_at, "retrieved_at")
    valid_at_utc = _utc(valid_at, "valid_at")
    interval_end_utc = _utc(interval_end, "interval_end")
    if provider_issued_at_utc > retrieved_at_utc:
        raise ValueError("provider_issued_at must not be after retrieved_at")
    if interval_end_utc <= valid_at_utc:
        raise ValueError("interval_end must be after valid_at")
    if ghi_unit != "W/m2":
        raise ValueError("ghi_unit must be W/m2")
    if cloud_cover_unit != "%":
        raise ValueError("cloud_cover_unit must be %")
    if temperature_unit == "K":
        temperature_c = _number(temperature, "temperature") - 273.15
    elif temperature_unit == "C":
        temperature_c = _number(temperature, "temperature")
    else:
        raise ValueError("temperature_unit must be C or K")
    if wind_speed is None:
        wind_speed_ms = None
    elif wind_speed_unit == "m/s":
        wind_speed_ms = _number(wind_speed, "wind_speed", 0)
    elif wind_speed_unit == "km/h":
        wind_speed_ms = _number(wind_speed, "wind_speed", 0) / 3.6
    else:
        raise ValueError("wind_speed_unit must be m/s or km/h when wind_speed is supplied")
    return NormalizedWeather(
        provider=_name(provider, "provider"), product=_name(product, "product"),
        mapping_version=_name(mapping_version, "mapping_version"),
        provider_issued_at_utc=provider_issued_at_utc,
        valid_at_utc=valid_at_utc, interval_end_utc=interval_end_utc,
        retrieved_at_utc=retrieved_at_utc,
        irradiance_global_wm2=_number(ghi, "ghi", 0),
        cloud_cover_pct=_number(cloud_cover, "cloud_cover", 0, 100),
        temperature_c=temperature_c,
        wind_speed_ms=wind_speed_ms,
        irradiance_direct_wm2=None if dni is None else _number(dni, "dni", 0),
        irradiance_diffuse_wm2=None if dhi is None else _number(dhi, "dhi", 0),
        relative_humidity_pct=None if humidity is None else _number(humidity, "humidity", 0, 100),
        precipitation_mm=None if precipitation is None else _number(precipitation, "precipitation", 0),
    )
