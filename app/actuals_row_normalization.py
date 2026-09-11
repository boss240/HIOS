"""Convert one approved provider row into a canonical actuals observation.

The caller resolves provider timestamps under the approved mapping before using
this module.  It makes no HTTP request, retains no raw payload and does not
write to the database.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from app.actual_generation_store import ActualGenerationObservation
from app.actuals_field_mapping import ActualsFieldMapping, canonicalize_measurements


def _field(row: Mapping[str, Any], name: str, label: str) -> Any:
    if name not in row:
        raise ValueError(f"provider row is missing mapped {label} field")
    return row[name]


def normalize_actuals_row(*, mapping: ActualsFieldMapping, row: Mapping[str, Any],
                          observed_at_utc: datetime, interval_end_utc: datetime,
                          retrieved_at_utc: datetime,
                          quality_flags: tuple[str, ...] = ()) -> ActualGenerationObservation:
    """Build an unstored observation from an already-approved mapping.

    Timestamp parsing remains outside this function because a provider mapping
    must explicitly establish its native timestamp format, timezone and interval
    boundary.  The required mapped timestamp fields are nevertheless checked
    for schema drift before an observation can be constructed.
    """
    if not isinstance(row, Mapping):
        raise ValueError("provider row must be a mapping")
    _field(row, mapping.observed_at_field, "observed_at")
    _field(row, mapping.interval_end_field, "interval_end")
    raw_power = _field(row, mapping.power_field, "power") if mapping.power_field else None
    raw_energy = _field(row, mapping.energy_field, "energy") if mapping.energy_field else None
    measurements = canonicalize_measurements(
        mapping, raw_power=raw_power, raw_energy=raw_energy,
    )
    status = None
    if mapping.status_field is not None:
        status = _field(row, mapping.status_field, "status")
        if status is not None and not isinstance(status, str):
            raise ValueError("mapped status field must be a string when supplied")
    return ActualGenerationObservation(
        provider=mapping.provider,
        mapping_version=mapping.mapping_version,
        observed_at_utc=observed_at_utc,
        interval_end_utc=interval_end_utc,
        retrieved_at_utc=retrieved_at_utc,
        ac_power_kw=measurements.ac_power_kw,
        energy_kwh=measurements.energy_kwh,
        energy_semantics=measurements.energy_semantics,
        device_status=status,
        quality_flags=quality_flags,
    )
