import hashlib
import json

import httpx
import pytest

from app.deye_openapi import DeyeApiError, DeyeCredentials, DeyeReadOnlyClient


def client(handler):
    return DeyeReadOnlyClient(DeyeCredentials("app", "secret", "a@example.com", "password"),
                              http=httpx.Client(transport=httpx.MockTransport(handler)))


def test_token_and_station_discovery_use_only_expected_read_requests():
    requests = []
    def handler(request):
        requests.append(request)
        if request.url.path.endswith("/token"):
            assert request.url.params["appId"] == "app"
            body = json.loads(request.content)
            assert body["companyId"] == "0"
            assert body["password"] == hashlib.sha256(b"password").hexdigest()
            return httpx.Response(200, json={"success": True, "accessToken": "raw-token"})
        return httpx.Response(200, json={"success": True, "data": []})
    api = client(handler)
    token = api.obtain_token()
    api.list_stations(token)
    assert [r.url.path for r in requests] == ["/v1.0/account/token", "/v1.0/station/list"]
    assert requests[1].headers["authorization"] == "bearer raw-token"


def test_history_is_bounded_and_rejects_control_paths():
    api = client(lambda request: httpx.Response(200, json={"success": True, "data": []}))
    assert api.station_history("Bearer token", 11, granularity=2, start_at="2026-09-01", end_at="2026-09-02")["success"]
    with pytest.raises(ValueError):
        api.station_history("Bearer token", 0, granularity=2, start_at="2026-09-01")
    with pytest.raises(DeyeApiError):
        api._post("/v1.0/order/sys/workMode/update", {})


def test_station_device_discovery_is_limited_to_one_or_two_pilots():
    requests = []
    api = client(lambda request: requests.append(request) or httpx.Response(200, json={"success": True}))

    api.station_devices("raw-token", (11, 22), page=1, size=20)

    assert json.loads(requests[0].content) == {"page": 1, "size": 20, "stationIds": [11, 22]}
    assert requests[0].headers["authorization"] == "bearer raw-token"
    with pytest.raises(ValueError):
        api.station_devices("raw-token", ())
    with pytest.raises(ValueError):
        api.station_devices("raw-token", (1, 2, 3))


def test_rejected_token_exposes_only_safe_endpoint_and_status_diagnostics():
    api = client(lambda request: httpx.Response(200, json={
        "success": False, "code": "2101025", "message": "secret response",
    }))

    with pytest.raises(DeyeApiError) as exc_info:
        api.obtain_token()

    error = exc_info.value
    assert error.endpoint == "/v1.0/account/token"
    assert error.status_code == 200
    assert error.provider_code == "2101025"
    assert "secret response" not in str(error)


def test_http_failure_exposes_safe_status_without_response_body():
    api = client(lambda request: httpx.Response(401, text="credential response"))

    with pytest.raises(DeyeApiError) as exc_info:
        api.obtain_token()

    error = exc_info.value
    assert error.endpoint == "/v1.0/account/token"
    assert error.status_code == 401
    assert "credential response" not in str(error)
