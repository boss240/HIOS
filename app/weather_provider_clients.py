"""Explicit read-only HTTP clients for the selected operational weather roles."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.weather_provider_credentials import ProviderApiKey
from app.weather_provider_requests import (
    GOOGLE_HOURLY_FORECAST_PATH,
    SOLCAST_RADIATION_FORECAST_PATH,
    GoogleHourlyForecastRequest,
    SolcastRadiationForecastRequest,
)
from app.weather_provider_response import (
    ProviderWeatherInterval,
    parse_google_hourly_forecast,
    parse_solcast_radiation_forecast,
)
from app.weather_provider_roles import WeatherProvider


GOOGLE_WEATHER_BASE_URL = "https://weather.googleapis.com"
SOLCAST_BASE_URL = "https://api.solcast.com.au"


@dataclass(frozen=True)
class WeatherProviderHttpError(RuntimeError):
    provider: WeatherProvider
    status_code: int | None = None

    def __str__(self) -> str:
        suffix = "network failure" if self.status_code is None else f"HTTP {self.status_code}"
        return f"{self.provider.value} read request failed: {suffix}"


def _json_response(*, provider: WeatherProvider, response: httpx.Response) -> dict[str, Any]:
    try:
        response.raise_for_status()
        body = response.json()
    except (httpx.HTTPError, ValueError) as error:
        status_code = error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None
        raise WeatherProviderHttpError(provider, status_code) from error
    if not isinstance(body, dict):
        raise WeatherProviderHttpError(provider, response.status_code)
    return body


class GoogleWeatherReadClient:
    """Caller-invoked Google hourly forecast reader; no retry or scheduling policy."""

    def __init__(self, key: ProviderApiKey, *, http: httpx.Client | None = None,
                 base_url: str = GOOGLE_WEATHER_BASE_URL) -> None:
        if key.provider is not WeatherProvider.GOOGLE_WEATHER:
            raise ValueError("Google client requires a Google Weather API key")
        if not base_url.startswith("https://"):
            raise ValueError("Google Weather base URL must use HTTPS")
        self._key = key
        self._http = http or httpx.Client(base_url=base_url, timeout=15.0)
        self._base_url = base_url.rstrip("/")

    def hourly_forecast(self, request: GoogleHourlyForecastRequest) -> tuple[ProviderWeatherInterval, ...]:
        params = request.query_parameters() | {"key": self._key.value}
        try:
            response = self._http.get(self._base_url + GOOGLE_HOURLY_FORECAST_PATH, params=params)
        except httpx.HTTPError as error:
            raise WeatherProviderHttpError(WeatherProvider.GOOGLE_WEATHER) from error
        return parse_google_hourly_forecast(_json_response(
            provider=WeatherProvider.GOOGLE_WEATHER, response=response,
        ))


class SolcastReadClient:
    """Caller-invoked Solcast irradiance reader; no retry or scheduling policy."""

    def __init__(self, key: ProviderApiKey, *, http: httpx.Client | None = None,
                 base_url: str = SOLCAST_BASE_URL) -> None:
        if key.provider is not WeatherProvider.SOLCAST:
            raise ValueError("Solcast client requires a Solcast API key")
        if not base_url.startswith("https://"):
            raise ValueError("Solcast base URL must use HTTPS")
        self._key = key
        self._http = http or httpx.Client(base_url=base_url, timeout=15.0)
        self._base_url = base_url.rstrip("/")

    def radiation_forecast(self, request: SolcastRadiationForecastRequest) -> tuple[ProviderWeatherInterval, ...]:
        try:
            response = self._http.get(
                self._base_url + SOLCAST_RADIATION_FORECAST_PATH,
                params=request.query_parameters(),
                headers={"Authorization": f"Bearer {self._key.value}", "Accept": "application/json"},
            )
        except httpx.HTTPError as error:
            raise WeatherProviderHttpError(WeatherProvider.SOLCAST) from error
        return parse_solcast_radiation_forecast(_json_response(
            provider=WeatherProvider.SOLCAST, response=response,
        ))
