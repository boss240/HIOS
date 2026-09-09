"""Fixed Sprint 2 weather-provider roles; no credential or network handling."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WeatherProvider(str, Enum):
    GOOGLE_WEATHER = "google_weather"
    SOLCAST = "solcast"
    OPENWEATHER_SOLAR = "openweather_solar"


class WeatherRole(str, Enum):
    OPERATIONAL_COVARIATES = "operational_covariates"
    OPERATIONAL_IRRADIANCE = "operational_irradiance"
    HISTORICAL_BACKTEST = "historical_backtest"


@dataclass(frozen=True)
class WeatherProviderProfile:
    provider: WeatherProvider
    roles: frozenset[WeatherRole]
    required_fields: frozenset[str]
    live_requests_allowed: bool


PROVIDER_PROFILES = {
    WeatherProvider.GOOGLE_WEATHER: WeatherProviderProfile(
        provider=WeatherProvider.GOOGLE_WEATHER,
        roles=frozenset({WeatherRole.OPERATIONAL_COVARIATES}),
        required_fields=frozenset({"cloud_cover_pct", "temperature_c", "wind_speed_ms"}),
        live_requests_allowed=True,
    ),
    WeatherProvider.SOLCAST: WeatherProviderProfile(
        provider=WeatherProvider.SOLCAST,
        roles=frozenset({WeatherRole.OPERATIONAL_IRRADIANCE}),
        required_fields=frozenset({
            "irradiance_global_wm2",
            "irradiance_direct_wm2",
            "irradiance_diffuse_wm2",
        }),
        live_requests_allowed=True,
    ),
    WeatherProvider.OPENWEATHER_SOLAR: WeatherProviderProfile(
        provider=WeatherProvider.OPENWEATHER_SOLAR,
        roles=frozenset({WeatherRole.HISTORICAL_BACKTEST}),
        required_fields=frozenset(),
        live_requests_allowed=False,
    ),
}


def profile_for(provider: WeatherProvider) -> WeatherProviderProfile:
    """Return the approved provider profile without external discovery."""
    return PROVIDER_PROFILES[provider]


def validate_live_provider_roles(*, covariates: WeatherProvider,
                                 irradiance: WeatherProvider) -> None:
    """Reject historical-only or incomplete sources from a live forecast path."""
    covariate_profile = profile_for(covariates)
    irradiance_profile = profile_for(irradiance)
    if not covariate_profile.live_requests_allowed or not irradiance_profile.live_requests_allowed:
        raise ValueError("historical-only weather providers cannot serve a live forecast")
    if WeatherRole.OPERATIONAL_COVARIATES not in covariate_profile.roles:
        raise ValueError("covariate provider is not approved for operational covariates")
    if WeatherRole.OPERATIONAL_IRRADIANCE not in irradiance_profile.roles:
        raise ValueError("irradiance provider is not approved for operational irradiance")
