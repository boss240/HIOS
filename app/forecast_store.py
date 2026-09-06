"""Tenant-safe persistence primitives for forecast runs; no scheduler or provider client."""
from dataclasses import dataclass
from datetime import datetime
import math
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class ForecastRun:
    run_id: UUID
    tenant_id: str
    plant_id: str
    forecast_origin_utc: datetime
    horizon_id: str
    model_id: str
    model_version: str
    feature_version: str
    input_hash: str
    configuration_hash: str
    code_commit: str
    status: str


@dataclass(frozen=True)
class ForecastPoint:
    interval_start_utc: datetime
    interval_end_utc: datetime
    predicted_power_kw: float
    predicted_energy_kwh: float
    quality_flags: tuple[str, ...] = ()
    provider_provenance: dict[str, str] | None = None


def create_or_get_run(database_url: str, subject: str, run: ForecastRun) -> UUID:
    """Create a logical run once, requiring active membership and tenant-owned plant.

    A retry returns the original run ID only when its signed caller still has active
    membership. The unique logical key intentionally excludes generated run_id.
    """
    if run.forecast_origin_utc.tzinfo is None:
        raise ValueError("forecast_origin_utc must be timezone-aware")
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        row = connection.execute(
            """WITH allowed AS (
                    SELECT 1 FROM membership
                    WHERE tenant_id = %s AND subject = %s AND active
                ), owned_plant AS (
                    SELECT 1 FROM plant
                    WHERE tenant_id = %s AND public_id = %s
                      AND EXISTS (SELECT 1 FROM allowed)
                ), inserted AS (
                    INSERT INTO forecast_run (
                        run_id, tenant_id, plant_id, forecast_origin_utc, horizon_id,
                        model_id, model_version, feature_version, input_hash,
                        configuration_hash, code_commit, status
                    )
                    SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    FROM owned_plant
                    ON CONFLICT (tenant_id, plant_id, forecast_origin_utc, horizon_id,
                                 model_id, model_version, input_hash) DO NOTHING
                    RETURNING run_id
                )
                SELECT run_id FROM inserted
                UNION ALL
                SELECT r.run_id FROM forecast_run r
                WHERE r.tenant_id = %s AND r.plant_id = %s
                  AND r.forecast_origin_utc = %s AND r.horizon_id = %s
                  AND r.model_id = %s AND r.model_version = %s AND r.input_hash = %s
                  AND EXISTS (SELECT 1 FROM owned_plant)
                LIMIT 1""",
            (run.tenant_id, subject, run.tenant_id, run.plant_id,
             run.run_id, run.tenant_id, run.plant_id, run.forecast_origin_utc,
             run.horizon_id, run.model_id, run.model_version, run.feature_version,
             run.input_hash, run.configuration_hash, run.code_commit, run.status,
             run.tenant_id, run.plant_id, run.forecast_origin_utc, run.horizon_id,
             run.model_id, run.model_version, run.input_hash),
        ).fetchone()
        if row is None:
            raise PermissionError("Active membership and tenant-owned plant are required")
        return row[0]


def publish_points(database_url: str, subject: str, tenant_id: str, run_id: UUID,
                   points: tuple[ForecastPoint, ...]) -> int:
    """Publish an immutable, idempotent point batch for an owned runnable forecast.

    There is no upsert: a retry can safely repeat the same intervals, while an
    altered prediction requires a new versioned run. Blocked runs cannot publish
    a stale result.
    """
    if not points:
        raise ValueError("at least one forecast point is required")
    values = []
    for point in points:
        if point.interval_start_utc.tzinfo is None or point.interval_end_utc.tzinfo is None:
            raise ValueError("forecast point timestamps must be timezone-aware")
        if point.interval_end_utc <= point.interval_start_utc:
            raise ValueError("forecast point interval_end_utc must be after interval_start_utc")
        for value, name in ((point.predicted_power_kw, "predicted_power_kw"),
                            (point.predicted_energy_kwh, "predicted_energy_kwh")):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f"{name} must be a finite non-negative number")
        values.append((run_id, point.interval_start_utc, point.interval_end_utc,
                       point.predicted_power_kw, point.predicted_energy_kwh,
                       Jsonb(list(point.quality_flags)), Jsonb(point.provider_provenance or {})))
    if len({value[1] for value in values}) != len(values):
        raise ValueError("forecast point interval_start_utc values must be unique per batch")
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        allowed = connection.execute(
            """SELECT 1 FROM forecast_run r JOIN membership m ON m.tenant_id = r.tenant_id
               WHERE r.run_id = %s AND r.tenant_id = %s AND m.subject = %s AND m.active
                 AND r.status IN ('normal', 'degraded')""",
            (run_id, tenant_id, subject),
        ).fetchone()
        if allowed is None:
            raise PermissionError("Active membership and runnable tenant-owned forecast are required")
        with connection.cursor() as cursor:
            cursor.executemany(
                """INSERT INTO forecast_point (
                       run_id, interval_start_utc, interval_end_utc, predicted_power_kw,
                       predicted_energy_kwh, quality_flags, provider_provenance
                   ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (run_id, interval_start_utc) DO NOTHING""",
                values,
            )
            return cursor.rowcount
