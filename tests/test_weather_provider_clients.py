import httpx
import pytest

from app.weather_provider_clients import (
    GoogleWeatherReadClient,
    SolcastReadClient,
    WeatherProviderHttpError,
)
from app.weather_provider_credentials import ProviderApiKey
from app.weather_provider_requests import GoogleHourlyForecastRequest, SolcastRadiationForecastRequest
from app.weather_provider_roles import WeatherProvider


def google_client(handler):
    return GoogleWeatherReadClient(
        ProviderApiKey(WeatherProvider.GOOGLE_WEATHER, "google-key"),
        http=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def solcast_client(handler):
    return SolcastReadClient(
        ProviderApiKey(WeatherProvider.SOLCAST, "solcast-key"),
        http=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_google_client_sends_key_only_to_google_and_parses_covariates():
    def handler(request):
        assert request.url.path == "/v1/forecast/hours:lookup"
        assert request.url.params["key"] == "google-key"
        return httpx.Response(200, json={"forecastHours": [{
            "interval": {"startTime": "2026-09-10T10:00:00Z", "endTime": "2026-09-10T11:00:00Z"},
            "temperature": {"degrees": 20, "unit": "CELSIUS"}, "cloudCover": 40,
            "wind": {"speed": {"value": 18, "unit": "KILOMETERS_PER_HOUR"}},
        }]})
    result = google_client(handler).hourly_forecast(GoogleHourlyForecastRequest(50, 30, 24))
    assert result[0].provider == "google_weather"


def test_solcast_client_sends_bearer_key_only_to_solcast_and_parses_irradiance():
    def handler(request):
        assert request.url.path == "/data/forecast/radiation_and_weather"
        assert request.headers["Authorization"] == "Bearer solcast-key"
        assert "key" not in request.url.params
        return httpx.Response(200, json={"forecasts": [{
            "period_end": "2026-09-10T11:00:00Z", "period": "PT60M",
            "ghi": 500, "dni": 300, "dhi": 200, "air_temp": 21, "wind_speed": 4,
        }]})
    result = solcast_client(handler).radiation_forecast(SolcastRadiationForecastRequest(50, 30))
    assert result[0].provider == "solcast"


@pytest.mark.parametrize("client", [
    lambda: google_client(lambda request: httpx.Response(401, text="provider secret response")),
    lambda: solcast_client(lambda request: httpx.Response(429, text="provider secret response")),
])
def test_http_failures_are_redacted(client):
    instance = client()
    request = GoogleHourlyForecastRequest(50, 30, 24) if isinstance(instance, GoogleWeatherReadClient) else SolcastRadiationForecastRequest(50, 30)
    method = instance.hourly_forecast if isinstance(instance, GoogleWeatherReadClient) else instance.radiation_forecast
    with pytest.raises(WeatherProviderHttpError) as exc_info:
        method(request)
    assert "provider secret response" not in str(exc_info.value)


def test_clients_reject_cross_provider_keys_and_non_https_base_urls():
    with pytest.raises(ValueError):
        GoogleWeatherReadClient(ProviderApiKey(WeatherProvider.SOLCAST, "key"))
    with pytest.raises(ValueError):
        SolcastReadClient(ProviderApiKey(WeatherProvider.GOOGLE_WEATHER, "key"))
    with pytest.raises(ValueError):
        GoogleWeatherReadClient(ProviderApiKey(WeatherProvider.GOOGLE_WEATHER, "key"), base_url="http://example.test")
