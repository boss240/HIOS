from datetime import date

import pytest

from app.deye_hourly_collection import collect_closed_pilot_day, hourly_coverage


class FakeDeye:
    def __init__(self):
        self.calls = []

    def obtain_token(self):
        self.calls.append("token")
        return "short-lived"

    def station_frame_history_for_day(self, token, station_id, *, closed_day_utc):
        self.calls.append((token, station_id, closed_day_utc))
        return {"stationDataItems": [
            {"timeStamp": 1_725_148_800, "generationPower": 1200, "generationValue": 1},
            {"timeStamp": 1_725_149_700, "generationPower": 1400, "generationValue": 1},
            {"timeStamp": "invalid", "generationPower": 0, "generationValue": 1},
        ]}


def test_coverage_groups_valid_frames_by_utc_hour_without_values():
    coverage = hourly_coverage({"stationDataItems": [
        {"timeStamp": 1_725_148_800, "generationPower": 12},
        {"timeStamp": 1_725_149_700, "generationPower": 13},
        {"timeStamp": "invalid", "generationPower": 0},
    ]})
    assert coverage == ({"hourUtc": "2024-09-01T00:00:00Z", "frameCount": 2},)


def test_collection_reads_one_closed_day_and_returns_aggregate_evidence(monkeypatch):
    client = FakeDeye()
    monkeypatch.setattr("app.deye_hourly_collection.datetime", type("Clock", (), {
        "now": staticmethod(lambda tz: __import__("datetime").datetime(2024, 9, 3, tzinfo=tz)),
        "fromtimestamp": staticmethod(__import__("datetime").datetime.fromtimestamp),
    }))
    report = collect_closed_pilot_day(client, station_id=7, closed_day_utc=date(2024, 9, 1))
    assert client.calls == ["token", ("short-lived", 7, date(2024, 9, 1))]
    assert report["stationId"] == "7"
    assert report["hourlyCoverage"] == ({"hourUtc": "2024-09-01T00:00:00Z", "frameCount": 2},)
    assert report["quality"]["sample_count"] == 3
    assert report["persistence"] == "not_written_pending_field_mapping"


@pytest.mark.parametrize("station_id", [0, -1, True, "7"])
def test_collection_rejects_invalid_station_id(station_id):
    with pytest.raises(ValueError):
        collect_closed_pilot_day(FakeDeye(), station_id=station_id, closed_day_utc=date(2024, 9, 1))


def test_collection_reuses_caller_token_without_another_authentication():
    class TokenReusingDeye:
        def __init__(self):
            self.calls = []

        def obtain_token(self):
            self.calls.append("token")
            return "unexpected"

        def station_frame_history_for_day(self, token, station_id, *, closed_day_utc):
            self.calls.append((token, station_id, closed_day_utc))
            return {"stationDataItems": []}

    client = TokenReusingDeye()
    report = collect_closed_pilot_day(client, station_id=7, closed_day_utc=date(2024, 9, 1), token="shared")
    assert client.calls == [("shared", 7, date(2024, 9, 1))]
    assert report["stationId"] == "7"
