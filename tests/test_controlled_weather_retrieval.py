from datetime import datetime, timedelta, timezone

import pytest

from app.controlled_weather_retrieval import retrieve_operational_weather
from app.operational_weather_composition import OperationalWeatherCompositionError
from app.weather_provider_requests import GoogleHourlyForecastRequest, SolcastRadiationForecastRequest
from app.weather_provider_response import ProviderWeatherInterval


START = datetime(2026, 9, 10, 10, tzinfo=timezone.utc)
END = START + timedelta(hours=1)


class GoogleReader:
    def __init__(self, rows): self.rows, self.requests = rows, []
    def hourly_forecast(self, request): self.requests.append(request); return self.rows


class SolcastReader:
    def __init__(self, rows): self.rows, self.requests = rows, []
    def radiation_forecast(self, request): self.requests.append(request); return self.rows


def test_reads_each_required_provider_once_and_composes_their_exact_intervals():
    google = GoogleReader((ProviderWeatherInterval("google_weather", START, END, {"cloud_cover_pct": 40, "temperature_c": 20, "wind_speed_ms": 5}),))
    solcast = SolcastReader((ProviderWeatherInterval("solcast", START, END, {"irradiance_global_wm2": 500, "irradiance_direct_wm2": 300, "irradiance_diffuse_wm2": 200}),))

    result = retrieve_operational_weather(
        google=google, solcast=solcast,
        google_request=GoogleHourlyForecastRequest(50, 30, 24),
        solcast_request=SolcastRadiationForecastRequest(50, 30),
    )

    assert len(google.requests) == len(solcast.requests) == 1
    assert result.google_interval_count == result.solcast_interval_count == 1
    assert result.intervals[0].irradiance_global_wm2 == 500


def test_does_not_retry_or_substitute_a_missing_required_provider_interval():
    google = GoogleReader((ProviderWeatherInterval("google_weather", START, END, {"cloud_cover_pct": 40, "temperature_c": 20, "wind_speed_ms": 5}),))
    solcast = SolcastReader(())

    with pytest.raises(OperationalWeatherCompositionError):
        retrieve_operational_weather(
            google=google, solcast=solcast,
            google_request=GoogleHourlyForecastRequest(50, 30, 24),
            solcast_request=SolcastRadiationForecastRequest(50, 30),
        )

    assert len(google.requests) == len(solcast.requests) == 1
