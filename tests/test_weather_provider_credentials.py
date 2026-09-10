import pytest

from app.weather_provider_credentials import (
    OperationalWeatherCredentials,
    ProviderApiKey,
    WeatherProviderConfigurationError,
    operational_credentials_from_environment,
)
from app.weather_provider_roles import WeatherProvider


def test_loads_only_the_approved_google_and_solcast_operational_keys():
    credentials = operational_credentials_from_environment({
        "GOOGLE_WEATHER_API_KEY": "google-secret",
        "SOLCAST_API_KEY": "solcast-secret",
        "OPENWEATHER_API_KEY": "historical-secret",
    })

    assert credentials.google_weather.provider is WeatherProvider.GOOGLE_WEATHER
    assert credentials.solcast.provider is WeatherProvider.SOLCAST
    assert "google-secret" not in repr(credentials)
    assert "solcast-secret" not in repr(credentials)


@pytest.mark.parametrize("environment", [
    {},
    {"GOOGLE_WEATHER_API_KEY": "key"},
    {"GOOGLE_WEATHER_API_KEY": " ", "SOLCAST_API_KEY": "key"},
])
def test_rejects_missing_or_blank_operational_keys(environment):
    with pytest.raises(WeatherProviderConfigurationError, match="missing weather provider"):
        operational_credentials_from_environment(environment)


def test_rejects_a_provider_key_in_the_wrong_operational_role():
    with pytest.raises(ValueError, match="operational covariates"):
        OperationalWeatherCredentials(
            google_weather=ProviderApiKey(WeatherProvider.SOLCAST, "key"),
            solcast=ProviderApiKey(WeatherProvider.SOLCAST, "key"),
        )
