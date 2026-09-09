"""As-of-safe exact-interval pairing of forecast power and measured actuals."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

import psycopg


def _name(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    if value.astimezone(timezone.utc) != value:
        raise ValueError(f"{name} must be UTC")
    return value


@dataclass(frozen=True)
class AlignedPowerSample:
    interval_start_utc: datetime
    interval_end_utc: datetime
    predicted_power_kw: float
    actual_power_kw: float
    actual_snapshot_id: UUID


def load_aligned_power_samples(*, database_url: str, subject: str, tenant_id: str,
                               plant_id: str, run_id: UUID, actual_provider: str,
                               actual_mapping_version: str,
                               actuals_as_of_utc: datetime) -> tuple[AlignedPowerSample, ...]:
    """Load exact interval pairs using only actual revisions known at an as-of cutoff.

    The newest eligible actual revision wins per interval. Rows retrieved after
    the cutoff are ignored even if they are present in the database today.
    """
    _name(subject, "subject")
    _name(tenant_id, "tenant_id")
    _name(plant_id, "plant_id")
    provider = _name(actual_provider, "actual_provider")
    mapping_version = _name(actual_mapping_version, "actual_mapping_version")
    cutoff = _utc(actuals_as_of_utc, "actuals_as_of_utc")

    with psycopg.connect(database_url, connect_timeout=5) as connection:
        allowed = connection.execute(
            """SELECT 1 FROM forecast_run r JOIN membership m ON m.tenant_id = r.tenant_id
               WHERE r.run_id = %s AND r.tenant_id = %s AND r.plant_id = %s
                 AND m.subject = %s AND m.active""",
            (run_id, tenant_id, plant_id, subject),
        ).fetchone()
        if allowed is None:
            raise PermissionError("Active membership and tenant-owned forecast run are required")
        rows = connection.execute(
            """WITH eligible_actuals AS (
                    SELECT DISTINCT ON (a.observed_at_utc, a.interval_end_utc)
                           a.snapshot_id, a.observed_at_utc, a.interval_end_utc, a.ac_power_kw
                    FROM actual_generation_snapshot a
                    WHERE a.tenant_id = %s AND a.plant_id = %s AND a.provider = %s
                      AND a.mapping_version = %s AND a.retrieved_at_utc <= %s
                      AND a.ac_power_kw IS NOT NULL
                    ORDER BY a.observed_at_utc, a.interval_end_utc,
                             a.retrieved_at_utc DESC, a.created_at DESC, a.snapshot_id DESC
                )
                SELECT p.interval_start_utc, p.interval_end_utc, p.predicted_power_kw,
                       a.ac_power_kw, a.snapshot_id
                FROM forecast_point p JOIN eligible_actuals a
                  ON a.observed_at_utc = p.interval_start_utc
                 AND a.interval_end_utc = p.interval_end_utc
                WHERE p.run_id = %s
                ORDER BY p.interval_start_utc""",
            (tenant_id, plant_id, provider, mapping_version, cutoff, run_id),
        ).fetchall()
    return tuple(AlignedPowerSample(*row) for row in rows)
