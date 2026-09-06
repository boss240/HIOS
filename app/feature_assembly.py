"""Versioned physical feature assembly for the deterministic MODEL-001 candidate."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math

from app.model_001 import Model001Input
from app.weather_normalization import NormalizedWeather


FEATURE_SCHEMA_VERSION = "model-001-features-v1"


def _finite(value: float, name: str, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    if maximum is not None and result > maximum:
        raise ValueError(f"{name} must be at most {maximum}")
    return result


def _utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class PlantGeometry:
    latitude_degrees: float
    longitude_degrees: float
    tilt_degrees: float
    surface_azimuth_degrees: float  # clockwise from north: south-facing is 180.
    ground_albedo: float = 0.2

    def __post_init__(self) -> None:
        _finite(self.latitude_degrees, "latitude_degrees", -90, 90)
        _finite(self.longitude_degrees, "longitude_degrees", -180, 180)
        _finite(self.tilt_degrees, "tilt_degrees", 0, 90)
        _finite(self.surface_azimuth_degrees, "surface_azimuth_degrees", 0, 360)
        _finite(self.ground_albedo, "ground_albedo", 0, 1)


@dataclass(frozen=True)
class Model001FeatureBundle:
    feature_schema_version: str
    interval_midpoint_utc: datetime
    solar_elevation_degrees: float
    solar_azimuth_degrees: float
    plane_of_array_irradiance_wm2: float
    model_input: Model001Input


def _solar_position(timestamp: datetime, geometry: PlantGeometry) -> tuple[float, float]:
    """Approximate solar elevation/azimuth from UTC and plant coordinates.

    The formula is deterministic and suitable for a candidate baseline. Its
    coefficient/version is pinned by FEATURE_SCHEMA_VERSION and must be evaluated
    against an approved solar library before production activation.
    """
    timestamp = _utc(timestamp, "timestamp")
    day = timestamp.timetuple().tm_yday
    minutes = timestamp.hour * 60 + timestamp.minute + timestamp.second / 60
    b = 2 * math.pi * (day - 81) / 364
    equation_of_time = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)
    declination = math.radians(23.44) * math.sin(2 * math.pi * (day - 81) / 365)
    hour_angle = math.radians(((minutes + equation_of_time + 4 * geometry.longitude_degrees) % 1440) / 4 - 180)
    latitude = math.radians(geometry.latitude_degrees)
    sin_elevation = (math.sin(latitude) * math.sin(declination) +
                     math.cos(latitude) * math.cos(declination) * math.cos(hour_angle))
    elevation = math.asin(max(-1.0, min(1.0, sin_elevation)))
    azimuth = math.atan2(math.sin(hour_angle),
                         math.cos(hour_angle) * math.sin(latitude) -
                         math.tan(declination) * math.cos(latitude)) + math.pi
    return math.degrees(elevation), math.degrees(azimuth) % 360


def build_model_001_features(*, weather: NormalizedWeather, geometry: PlantGeometry,
                             forecast_origin_utc: datetime) -> Model001FeatureBundle:
    """Build one as-issued feature bundle; missing DNI/DHI blocks publication."""
    origin = _utc(forecast_origin_utc, "forecast_origin_utc")
    if weather.provider_issued_at_utc > origin or weather.retrieved_at_utc > origin:
        raise ValueError("weather was not available at forecast_origin_utc")
    if weather.irradiance_direct_wm2 is None or weather.irradiance_diffuse_wm2 is None:
        raise ValueError("DNI and DHI are required; no undocumented decomposition is applied")
    midpoint = weather.valid_at_utc + (weather.interval_end_utc - weather.valid_at_utc) / 2
    elevation, solar_azimuth = _solar_position(midpoint, geometry)
    tilt = math.radians(geometry.tilt_degrees)
    incidence = (math.sin(math.radians(elevation)) * math.cos(tilt) +
                 math.cos(math.radians(elevation)) * math.sin(tilt) *
                 math.cos(math.radians(solar_azimuth - geometry.surface_azimuth_degrees)))
    poa = (weather.irradiance_direct_wm2 * max(0.0, incidence) +
           weather.irradiance_diffuse_wm2 * (1 + math.cos(tilt)) / 2 +
           weather.irradiance_global_wm2 * geometry.ground_albedo * (1 - math.cos(tilt)) / 2)
    if elevation <= 0:
        poa = 0.0
    model_input = Model001Input(
        plane_of_array_irradiance_wm2=max(0.0, poa), cell_temperature_c=weather.temperature_c,
        solar_elevation_degrees=elevation,
    )
    return Model001FeatureBundle(FEATURE_SCHEMA_VERSION, midpoint, elevation, solar_azimuth,
                                 model_input.plane_of_array_irradiance_wm2, model_input)
