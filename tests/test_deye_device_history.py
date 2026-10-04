from datetime import date, datetime, timezone
import json
import httpx
import pytest
from app.deye_openapi import DeyeCredentials, DeyeReadOnlyClient


def client(handler):
    return DeyeReadOnlyClient(DeyeCredentials('id', 'secret', 'email', 'password'),
                              http=httpx.Client(transport=httpx.MockTransport(handler)))


def test_history_requests_only_solar_points_for_exact_utc_day():
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={'success': True, 'dataList': []})
    result = client(handler).device_solar_history_for_day(
        'token', 'selected-device', closed_day_utc=date(2020, 1, 1))
    assert result['dataList'] == []
    assert len(requests) == 1
    assert requests[0].url.path == '/v1.0/device/historyRaw'
    assert json.loads(requests[0].content) == {
        'deviceSn': 'selected-device', 'startTimestamp': 1577836800,
        'endTimestamp': 1577923199,
        'measurePoints': ['TotalSolarPower', 'PVDailyPowerGenerationActive']}


@pytest.mark.parametrize('serial', ['', ' padded ', None, 'x' * 129])
def test_invalid_serial_never_calls_provider(serial):
    def forbidden(request):
        pytest.fail('invalid input reached provider')
    with pytest.raises(ValueError):
        client(forbidden).device_solar_history_for_day(
            'token', serial, closed_day_utc=date(2020, 1, 1))


@pytest.mark.parametrize('day', [None, '2020-01-01', datetime(2020, 1, 1),
                               datetime.now(timezone.utc).date(), date(9999, 1, 1)])
def test_unclosed_or_ambiguous_day_never_calls_provider(day):
    def forbidden(request):
        pytest.fail('invalid day reached provider')
    with pytest.raises(ValueError):
        client(forbidden).device_solar_history_for_day(
            'token', 'selected-device', closed_day_utc=day)
