"""Pure quality checks for a bounded Deye station-history response.

The checks intentionally do not map provider fields to HIOS actuals, persist
anything, or call Deye.  They provide aggregate evidence for the separate
field-mapping approval gate.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping


@dataclass(frozen=True)
class DeyeFrameQuality:
    """Non-sensitive summary of one bounded station-history response."""

    sample_count: int
    valid_timestamp_count: int
    cadence_seconds: tuple[int, ...]
    generation_power_numeric_count: int
    generation_value_numeric_count: int
    flags: tuple[str, ...]


def _items(body: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return the documented frame rows without accepting alternate payloads."""
    rows = body.get("stationDataItems")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, Mapping)]


def _finite_non_negative(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
        and value >= 0
    )


def audit_station_frame_history(body: Mapping[str, Any]) -> DeyeFrameQuality:
    """Summarise frame data quality without returning rows or native identifiers.

    ``timeStamp`` is checked only as a candidate ten-digit Unix-epoch-seconds
    field.  Numeric generation fields are checked for basic shape, not unit or
    meter semantics.  Any flag blocks automatic field mapping.
    """
    rows = _items(body)
    flags: set[str] = set()
    if not rows:
        return DeyeFrameQuality(0, 0, (), 0, 0, ("station_data_items_missing",))

    timestamps: list[int] = []
    power_count = 0
    energy_count = 0
    for row in rows:
        timestamp = row.get("timeStamp")
        if not _finite_non_negative(timestamp) or int(timestamp) != timestamp:
            flags.add("timestamp_invalid")
        elif not 1_000_000_000 <= int(timestamp) <= 9_999_999_999:
            flags.add("timestamp_not_epoch_seconds_candidate")
        else:
            timestamps.append(int(timestamp))

        for field, flag, counter in (
            ("generationPower", "generation_power_invalid", "power"),
            ("generationValue", "generation_value_invalid", "energy"),
        ):
            if field not in row:
                flags.add(f"{field}_missing")
            elif _finite_non_negative(row[field]):
                if counter == "power":
                    power_count += 1
                else:
                    energy_count += 1
            else:
                flags.add(flag)

    cadence: tuple[int, ...] = ()
    if timestamps:
        if len(timestamps) != len(set(timestamps)):
            flags.add("timestamp_duplicate")
        if timestamps != sorted(timestamps):
            flags.add("timestamp_not_monotonic")
        ordered = sorted(set(timestamps))
        cadence = tuple(sorted({later - earlier for earlier, later in zip(ordered, ordered[1:])}))
        if len(cadence) > 1:
            flags.add("cadence_irregular")
    else:
        flags.add("timestamp_missing")

    return DeyeFrameQuality(
        sample_count=len(rows),
        valid_timestamp_count=len(timestamps),
        cadence_seconds=cadence,
        generation_power_numeric_count=power_count,
        generation_value_numeric_count=energy_count,
        flags=tuple(sorted(flags)),
    )
