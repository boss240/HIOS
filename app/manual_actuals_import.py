"""Validate a manual Deye hourly CSV before any field mapping or persistence."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from io import StringIO
import math

_REQUIRED = ("plant_key", "interval_start_utc", "interval_end_utc", "ac_power_kw", "energy_kwh", "energy_semantics", "device_status", "source_reference")
_PILOTS = {"deye-pilot-pohreby", "deye-pilot-borshchiv"}


def _utc(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError(f"{label} must be ISO 8601 UTC") from error
    if parsed.tzinfo is None or parsed.astimezone(timezone.utc) != parsed:
        raise ValueError(f"{label} must be UTC")
    return parsed


def _number(value: str, label: str) -> None:
    if not value.strip():
        return
    try:
        number = float(value)
    except ValueError as error:
        raise ValueError(f"{label} must be numeric") from error
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{label} must be finite and non-negative")


def preview_manual_actuals_csv(content: str) -> dict[str, object]:
    if not isinstance(content, str) or len(content.encode("utf-8")) > 2_000_000:
        raise ValueError("CSV must be non-empty and at most 2 MB")
    rows = [line for line in content.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    reader = csv.DictReader(StringIO("\n".join(rows)))
    if tuple(reader.fieldnames or ()) != _REQUIRED:
        raise ValueError("CSV headers do not match the HIOS Deye template")
    counts = {pilot: 0 for pilot in _PILOTS}
    for position, row in enumerate(reader, start=2):
        pilot = (row.get("plant_key") or "").strip()
        if pilot not in _PILOTS:
            raise ValueError(f"row {position}: unknown pilot key")
        start = _utc(row["interval_start_utc"], f"row {position} interval_start_utc")
        end = _utc(row["interval_end_utc"], f"row {position} interval_end_utc")
        if end <= start:
            raise ValueError(f"row {position}: interval end must be after start")
        _number(row["ac_power_kw"], f"row {position} ac_power_kw")
        _number(row["energy_kwh"], f"row {position} energy_kwh")
        if not row["ac_power_kw"].strip() and not row["energy_kwh"].strip():
            raise ValueError(f"row {position}: power or energy is required")
        if row["energy_kwh"].strip() and row["energy_semantics"] not in {"interval", "cumulative"}:
            raise ValueError(f"row {position}: energy_semantics is invalid")
        if not (row["source_reference"] or "").strip():
            raise ValueError(f"row {position}: source_reference is required")
        counts[pilot] += 1
    if not sum(counts.values()):
        raise ValueError("CSV has no data rows")
    return {"rows": sum(counts.values()), "byPilot": counts, "persistence": "not_written_pending_field_mapping"}
