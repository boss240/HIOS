"""Bounded, read-only Deye collection evidence for two named pilot stations.

The module deliberately returns coverage and quality evidence only.  It never
stores raw provider rows, maps their units, or exposes a Deye control action.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, timezone
from typing import Any, Mapping

from app.deye_frame_quality import audit_station_frame_history
from app.deye_openapi import DeyeReadOnlyClient


def _frame_rows(body: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = body.get("stationDataItems")
    return [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, list) else []


def hourly_coverage(body: Mapping[str, Any]) -> tuple[dict[str, int], ...]:
    """Return UTC-hour frame counts without retaining timestamps or values."""
    counts: dict[str, int] = {}
    for row in _frame_rows(body):
        value = row.get("timeStamp")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
            continue
        timestamp = int(value)
        if not 1_000_000_000 <= timestamp <= 9_999_999_999:
            continue
        hour = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%dT%H:00:00Z")
        counts[hour] = counts.get(hour, 0) + 1
    return tuple({"hourUtc": hour, "frameCount": counts[hour]} for hour in sorted(counts))


def collect_closed_pilot_day(client: DeyeReadOnlyClient, *, station_id: int,
                              closed_day_utc: date, token: str | None = None) -> dict[str, Any]:
    """Read one closed UTC day and return aggregate coverage, never raw frames."""
    if isinstance(station_id, bool) or not isinstance(station_id, int) or station_id <= 0:
        raise ValueError("station_id must be a positive integer")
    if isinstance(closed_day_utc, datetime) or not isinstance(closed_day_utc, date):
        raise ValueError("closed_day_utc must be a date")
    if closed_day_utc >= datetime.now(timezone.utc).date():
        raise ValueError("closed_day_utc must be before today")
    request_token = token or client.obtain_token()
    response = client.station_frame_history_for_day(request_token, station_id, closed_day_utc=closed_day_utc)
    quality = asdict(audit_station_frame_history(response))
    return {
        "dateUtc": closed_day_utc.isoformat(),
        "stationId": str(station_id),
        "hourlyCoverage": hourly_coverage(response),
        "quality": quality,
        "persistence": "not_written_pending_field_mapping",
    }
