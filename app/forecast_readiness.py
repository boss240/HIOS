"""Tenant-safe, per-plant forecast-data readiness for the ensemble workflow."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import psycopg


@dataclass(frozen=True)
class ForecastReadiness:
    plant_id: str
    plant_name: str
    cloud_status: str | None
    actual_interval_count: int
    first_actual_at_utc: datetime | None
    last_actual_at_utc: datetime | None
    provider_count: int
    calibrated_provider_count: int
    state: str


def list_readiness(*, database_url: str, tenant_id: str, subject: str) -> tuple[ForecastReadiness, ...]:
    """List each owned plant's next safe forecasting step without exposing credentials or payloads."""
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        allowed = connection.execute(
            "SELECT EXISTS(SELECT 1 FROM membership WHERE tenant_id=%s AND subject=%s AND active)",
            (tenant_id, subject),
        ).fetchone()[0]
        if not allowed:
            raise PermissionError("Active membership is required")
        rows = connection.execute(
            """SELECT p.public_id, p.name,
                      (SELECT min(r.status) FROM inverter_cloud_connection_request r
                       WHERE r.tenant_id=p.tenant_id AND r.plant_id=p.public_id),
                      (SELECT count(*) FROM actual_generation_snapshot a
                       WHERE a.tenant_id=p.tenant_id AND a.plant_id=p.public_id),
                      (SELECT min(a.observed_at_utc) FROM actual_generation_snapshot a
                       WHERE a.tenant_id=p.tenant_id AND a.plant_id=p.public_id),
                      (SELECT max(a.interval_end_utc) FROM actual_generation_snapshot a
                       WHERE a.tenant_id=p.tenant_id AND a.plant_id=p.public_id),
                      (SELECT count(*) FROM weather_provider_channel w
                       WHERE w.tenant_id=p.tenant_id AND w.status='configured'),
                      (SELECT count(*) FROM provider_ensemble_profile e
                       WHERE e.tenant_id=p.tenant_id AND e.plant_id=p.public_id)
               FROM plant p
               WHERE p.tenant_id=%s
               ORDER BY p.created_at DESC, p.public_id COLLATE \"C\"""",
            (tenant_id,),
        ).fetchall()
    result = []
    for plant_id, name, cloud_status, actuals, first_actual, last_actual, providers, calibrated in rows:
        if calibrated:
            state = "calibrated"
        elif actuals:
            state = "calibration_pending"
        elif cloud_status and cloud_status != "verified":
            state = "awaiting_cloud_authorization"
        else:
            state = "awaiting_actuals"
        result.append(ForecastReadiness(
            plant_id, name, cloud_status, actuals, first_actual, last_actual, providers, calibrated, state
        ))
    return tuple(result)

