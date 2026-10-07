import httpx
import pytest

from app.weather_provider_clients import WeatherProviderHttpError, _json_response
from app.weather_provider_roles import WeatherProvider


@pytest.mark.parametrize('status,code', [
    (401, 'WEATHER_PROVIDER_AUTHENTICATION_FAILED'),
    (402, 'WEATHER_PROVIDER_PLAN_LIMIT'),
    (403, 'WEATHER_PROVIDER_ACCESS_DENIED'),
    (429, 'WEATHER_PROVIDER_RATE_LIMIT'),
    (500, 'WEATHER_PROVIDER_UNAVAILABLE'),
    (None, 'WEATHER_PROVIDER_UNAVAILABLE'),
])
def test_failure_reason_is_safe_and_distinguishes_plan_from_authentication(status, code):
    error = WeatherProviderHttpError(WeatherProvider.SOLCAST, status)
    assert error.public_code == code


def test_provider_body_and_secret_url_are_not_public_error_details():
    response = httpx.Response(402, json={'message': 'private provider account'},
        request=httpx.Request('GET', 'https://example.test/?api_key=private-key'))
    with pytest.raises(WeatherProviderHttpError) as caught:
        _json_response(provider=WeatherProvider.SOLCAST, response=response)
    assert caught.value.public_code == 'WEATHER_PROVIDER_PLAN_LIMIT'
    assert 'private' not in str(caught.value)
