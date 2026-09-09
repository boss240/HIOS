import pytest

from app.weather_provider_roles import (
    WeatherProvider,
    WeatherRole,
    profile_for,
    validate_live_provider_roles,
)


def test_selected_provider_profiles_keep_distinct_roles():
    google = profile_for(WeatherProvider.GOOGLE_WEATHER)
    solcast = profile_for(WeatherProvider.SOLCAST)
    openweather = profile_for(WeatherProvider.OPENWEATHER_SOLAR)

    assert WeatherRole.OPERATIONAL_COVARIATES in google.roles
    assert "irradiance_global_wm2" not in google.required_fields
    assert WeatherRole.OPERATIONAL_IRRADIANCE in solcast.roles
    assert "irradiance_direct_wm2" in solcast.required_fields
    assert openweather.roles == frozenset({WeatherRole.HISTORICAL_BACKTEST})
    assert openweather.live_requests_allowed is False


def test_only_google_plus_solcast_passes_live_role_validation():
    validate_live_provider_roles(
        covariates=WeatherProvider.GOOGLE_WEATHER,
        irradiance=WeatherProvider.SOLCAST,
    )

    with pytest.raises(ValueError, match="operational irradiance"):
        validate_live_provider_roles(
            covariates=WeatherProvider.GOOGLE_WEATHER,
            irradiance=WeatherProvider.GOOGLE_WEATHER,
        )
    with pytest.raises(ValueError, match="historical-only"):
        validate_live_provider_roles(
            covariates=WeatherProvider.OPENWEATHER_SOLAR,
            irradiance=WeatherProvider.SOLCAST,
        )
