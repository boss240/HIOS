"""One explicit Google-plus-Solcast retrieval for a controlled Sprint 2 run."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.operational_weather_composition import (
    OperationalWeatherInterval,
    compose_operational_weather,
)
from app.weather_provider_requests import GoogleHourlyForecastRequest, SolcastRadiationForecastRequest
from app.weather_provider_response import ProviderWeatherInterval


class GoogleHourlyReader(Protocol):
    def hourly_forecast(self, request: GoogleHourlyForecastRequest) -> tuple[ProviderWeatherInterval, ...]: ...


class SolcastRadiationReader(Protocol):
    def radiation_forecast(self, request: SolcastRadiationForecastRequest) -> tuple[ProviderWeatherInterval, ...]: ...


@dataclass(frozen=True)
class ControlledWeatherRetrieval:
    """The composed intervals and source-row counts for one caller-invoked read."""

    intervals: tuple[OperationalWeatherInterval, ...]
    google_interval_count: int
    solcast_interval_count: int


def retrieve_operational_weather(*, google: GoogleHourlyReader,
                                 solcast: SolcastRadiationReader,
                                 google_request: GoogleHourlyForecastRequest,
                                 solcast_request: SolcastRadiationForecastRequest) -> ControlledWeatherRetrieval:
    """Read both mandatory sources once, then require exact interval composition.

    No provider is optional in the approved production contour.  Retry, deadline
    and fallback decisions remain in the separately configured failover policy;
    this function intentionally performs no implicit retry or side effect.
    """
    google_intervals = google.hourly_forecast(google_request)
    solcast_intervals = solcast.radiation_forecast(solcast_request)
    return ControlledWeatherRetrieval(
        intervals=compose_operational_weather(google=google_intervals, solcast=solcast_intervals),
        google_interval_count=len(google_intervals),
        solcast_interval_count=len(solcast_intervals),
    )
