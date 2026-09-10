"""Secret-safe configuration boundary for the approved operational weather roles.

The module validates configuration only.  It performs no provider discovery,
HTTP requests, scheduling, or persistence.  Callers must inject the returned
credentials into an explicitly invoked adapter.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from app.weather_provider_roles import WeatherProvider, validate_live_provider_roles


class WeatherProviderConfigurationError(ValueError):
    """A required provider secret is unavailable or malformed."""


@dataclass(frozen=True)
class ProviderApiKey:
    provider: WeatherProvider
    value: str = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise WeatherProviderConfigurationError(
                f"{self.provider.value} API key must be a non-empty string"
            )


@dataclass(frozen=True)
class OperationalWeatherCredentials:
    """Credentials for the fixed Google-plus-Solcast production contour."""

    google_weather: ProviderApiKey
    solcast: ProviderApiKey

    def __post_init__(self) -> None:
        validate_live_provider_roles(
            covariates=self.google_weather.provider,
            irradiance=self.solcast.provider,
        )


def operational_credentials_from_environment(
    environment: Mapping[str, str] | None = None,
) -> OperationalWeatherCredentials:
    """Load only the two approved operational secrets from an injected mapping.

    The function deliberately does not accept an OpenWeather secret because
    OpenWeather Solar is historical-only in Sprint 2.
    """
    import os

    source = os.environ if environment is None else environment
    names = {
        "GOOGLE_WEATHER_API_KEY": WeatherProvider.GOOGLE_WEATHER,
        "SOLCAST_API_KEY": WeatherProvider.SOLCAST,
    }
    missing = [name for name in names if not isinstance(source.get(name), str) or not source[name].strip()]
    if missing:
        raise WeatherProviderConfigurationError(
            "missing weather provider environment variables: " + ", ".join(missing)
        )
    return OperationalWeatherCredentials(
        google_weather=ProviderApiKey(WeatherProvider.GOOGLE_WEATHER, source["GOOGLE_WEATHER_API_KEY"]),
        solcast=ProviderApiKey(WeatherProvider.SOLCAST, source["SOLCAST_API_KEY"]),
    )
