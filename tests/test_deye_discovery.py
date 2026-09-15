import pytest

from app.deye_discovery import client_from_environment, discover_stations


class FakeDeye:
    def obtain_token(self):
        return "token"

    def list_stations(self, token, *, page, size):
        assert token == "token"
        assert (page, size) == (1, 100)
        return {"data": {"records": [
            {"stationName": "Погреби", "stationId": 7},
            {"stationName": "Борщів", "stationId": 9},
        ]}}


def test_discovery_only_returns_station_choices():
    choices = discover_stations(FakeDeye())
    assert [(choice.station_id, choice.name) for choice in choices] == [(9, "Борщів"), (7, "Погреби")]


def test_configuration_requires_all_server_side_values():
    with pytest.raises(ValueError, match="not configured"):
        client_from_environment({"DEYE_APP_ID": "only-one-value"})
