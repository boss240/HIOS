"""Bounded, read-only Deye telemetry inspection for field-mapping approval."""
from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any

from app.deye_frame_quality import audit_station_frame_history
from app.deye_openapi import DeyeReadOnlyClient


def inspect_station_day(client: DeyeReadOnlyClient, *, station_id: int,
                        closed_day_utc: date) -> dict[str, Any]:
    """Fetch one past UTC day and return only an aggregate quality report.

    The function intentionally does not retain raw rows, create actuals, or
    issue any Deye command. A separately approved field mapping is required
    before telemetry can enter the forecasting evidence store.
    """
    if isinstance(station_id, bool) or not isinstance(station_id, int) or station_id <= 0:
        raise ValueError("station_id must be a positive integer")
    token = client.obtain_token()
    response = client.station_frame_history_for_day(token, station_id, closed_day_utc=closed_day_utc)
    report = asdict(audit_station_frame_history(response))
    report["dateUtc"] = closed_day_utc.isoformat()
    report["stationId"] = str(station_id)
    report["persistence"] = "not_written"
    return report
