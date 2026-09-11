import importlib.util
from pathlib import Path

import pytest


spec = importlib.util.spec_from_file_location(
    "deye_pilot_discovery", Path("scripts/deye_pilot_discovery.py")
)
assert spec is not None
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class FakeDeye:
    def obtain_token(self):
        return "Bearer test"

    def list_stations(self, token):
        return {
            "data": {
                "records": [
                    {"stationName": "Погреби Каштанова 15а", "stationId": 101},
                    {"stationName": "Борщів Борщів", "stationId": 202},
                    {"stationName": "Other", "stationId": 303},
                ]
            }
        }


def test_discovery_returns_only_two_approved_pilots():
    assert module.discover_pilots(FakeDeye()) == (
        {"pilot_key": "deye-pilot-borshchiv", "station_id": 202},
        {"pilot_key": "deye-pilot-pohreby", "station_id": 101},
    )


def test_discovery_accepts_documented_top_level_station_list_shape():
    class DeyeStationList(FakeDeye):
        def list_stations(self, token):
            return {"stationList": [
                {"name": "Погреби", "id": 101},
                {"name": "Борщів", "id": 202},
            ]}

    assert module.discover_pilots(DeyeStationList()) == (
        {"pilot_key": "deye-pilot-borshchiv", "station_id": 202},
        {"pilot_key": "deye-pilot-pohreby", "station_id": 101},
    )


def test_discovery_rejects_missing_pilot_and_environment():
    class Missing(FakeDeye):
        def list_stations(self, token):
            return {"data": [{"stationName": "Погреби", "stationId": 101}]}

    with pytest.raises(ValueError, match="both approved"):
        module.discover_pilots(Missing())
    with pytest.raises(ValueError, match="DEYE_APP_SECRET"):
        module.credentials_from_environment({"DEYE_APP_ID": "id"})
