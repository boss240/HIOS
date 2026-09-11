"""Pure request contracts for the approved Sprint 2 weather providers.

These types validate request shape only.  They do not contain API keys, make
HTTP calls, paginate responses, or enable a scheduler.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


GOOGLE_HOURLY_FORECAST_PATH = "/v1/forecast/hours:lookup"
SOLCAST_RADIATION_FORECAST_PATH = "/data/forecast/radiation_and_weather"
SOLCAST_OUTPUT_PARAMETERS = "ghi,dni,dhi,air_temp,wind_speed_10m"


def _coordinate(value: float, *, name: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if result < minimum or result > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return result


@dataclass(frozen=True)
class GoogleHourlyForecastRequest:
    latitude: float
    longitude: float
    hours: int
    page_size: int = 24
    page_token: str | None = None

    def __post_init__(self) -> None:
        _coordinate(self.latitude, name="latitude", minimum=-90, maximum=90)
        _coordinate(self.longitude, name="longitude", minimum=-180, maximum=180)
        if not isinstance(self.hours, int) or not 1 <= self.hours <= 240:
            raise ValueError("hours must be an integer from 1 to 240")
        if not isinstance(self.page_size, int) or not 1 <= self.page_size <= 24:
            raise ValueError("page_size must be an integer from 1 to 24")
        if self.page_token is not None and (not isinstance(self.page_token, str) or not self.page_token.strip()):
            raise ValueError("page_token must be a non-empty string when supplied")

    def query_parameters(self) -> dict[str, str]:
        values = {
            "location.latitude": str(self.latitude),
            "location.longitude": str(self.longitude),
            "hours": str(self.hours),
            "pageSize": str(self.page_size),
            "unitsSystem": "METRIC",
        }
        if self.page_token:
            values["pageToken"] = self.page_token
        return values


@dataclass(frozen=True)
class SolcastRadiationForecastRequest:
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        _coordinate(self.latitude, name="latitude", minimum=-90, maximum=90)
        _coordinate(self.longitude, name="longitude", minimum=-180, maximum=180)

    def query_parameters(self) -> dict[str, str]:
        return {
            "latitude": str(self.latitude),
            "longitude": str(self.longitude),
            "format": "json",
            "output_parameters": SOLCAST_OUTPUT_PARAMETERS,
        }
