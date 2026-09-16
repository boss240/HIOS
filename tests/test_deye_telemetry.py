from datetime import date

import pytest

from app.deye_telemetry import inspect_station_day


class FakeDeye:
    def __init__(self): self.calls = []
    def obtain_token(self):
        self.calls.append("token")
        return "short-lived-token"
    def station_frame_history_for_day(self, token, station_id, *, closed_day_utc):
        self.calls.append((token, station_id, closed_day_utc))
        return {"stationDataItems": [
            {"timeStamp": 1_726_000_000, "generationPower": 1200, "generationValue": 3.4},
            {"timeStamp": 1_726_000_900, "generationPower": 0, "generationValue": 0},
        ]}


def test_inspection_reads_one_closed_day_and_returns_only_aggregate_quality():
    client = FakeDeye()
    report = inspect_station_day(client, station_id=7, closed_day_utc=date(2024, 9, 18))
    assert client.calls == ["token", ("short-lived-token", 7, date(2024, 9, 18))]
    assert report == {"sample_count": 2, "valid_timestamp_count": 2, "cadence_seconds": (900,),
                      "generation_power_numeric_count": 2, "generation_value_numeric_count": 2,
                      "flags": (), "dateUtc": "2024-09-18", "stationId": "7", "persistence": "not_written"}


@pytest.mark.parametrize("station_id", [0, -1, True, "7"])
def test_inspection_rejects_invalid_station_id(station_id):
    with pytest.raises(ValueError):
        inspect_station_day(FakeDeye(), station_id=station_id, closed_day_utc=date(2024, 9, 18))
