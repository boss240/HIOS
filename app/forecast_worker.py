"""One controlled forecast-worker attempt; scheduler process remains external."""
from dataclasses import dataclass
from uuid import UUID, uuid4

import psycopg

from app.feature_assembly import PlantGeometry
from app.forecast_job import ForecastWeatherInput, execute_model_001
from app.forecast_schedule import JobKey, claim_lease, release_lease
from app.forecast_store import ForecastRun
from app.model_001 import Model001Config


@dataclass(frozen=True)
class WorkerAttempt:
    outcome_id: UUID | None
    status: str
    run_id: UUID | None = None
    published_points: int | None = None


def _start_outcome(database_url: str, subject: str, key: JobKey, lease_id: UUID, outcome_id: UUID) -> None:
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        row = connection.execute(
            """WITH held AS (
                    SELECT 1 FROM forecast_job_lease l JOIN membership m ON m.tenant_id=l.tenant_id
                    WHERE l.tenant_id=%s AND l.plant_id=%s AND l.forecast_origin_utc=%s
                      AND l.horizon_id=%s AND l.lease_id=%s AND l.claimed_by=%s
                      AND m.subject=%s AND m.active
                ), inserted AS (
                    INSERT INTO forecast_job_outcome (
                        outcome_id, lease_id, tenant_id, plant_id, forecast_origin_utc, horizon_id, status, claimed_by
                    ) SELECT %s, %s, %s, %s, %s, %s, 'running', %s FROM held
                    RETURNING 1
                ) SELECT EXISTS (SELECT 1 FROM inserted)""",
            (key.tenant_id, key.plant_id, key.forecast_origin_utc, key.horizon_id, lease_id, subject, subject,
             outcome_id, lease_id, key.tenant_id, key.plant_id, key.forecast_origin_utc, key.horizon_id, subject),
        ).fetchone()
        if not row[0]:
            raise PermissionError("A held tenant-scoped forecast lease is required")


def _finish_outcome(database_url: str, subject: str, outcome_id: UUID, *, status: str,
                    run_id: UUID | None = None, published_points: int | None = None,
                    error_class: str | None = None) -> None:
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        row = connection.execute(
            """UPDATE forecast_job_outcome o SET status=%s, completed_at=now(), forecast_run_id=%s,
                   published_points=%s, error_class=%s
               WHERE o.outcome_id=%s AND o.status='running' AND o.claimed_by=%s
                 AND EXISTS (SELECT 1 FROM membership m WHERE m.tenant_id=o.tenant_id
                             AND m.subject=%s AND m.active)
               RETURNING outcome_id""",
            (status, run_id, published_points, error_class, outcome_id, subject, subject),
        ).fetchone()
        if row is None:
            raise PermissionError("Only the active worker owner may finish this outcome")


def run_once(*, database_url: str, subject: str, key: JobKey, lease_id: UUID,
             run: ForecastRun, config: Model001Config, geometry: PlantGeometry,
             weather_inputs: tuple[ForecastWeatherInput, ...], lease_ttl_seconds: int = 300) -> WorkerAttempt:
    """Claim, execute, audit and always release one logical forecast attempt."""
    if (key.tenant_id, key.plant_id, key.forecast_origin_utc, key.horizon_id) != (
        run.tenant_id, run.plant_id, run.forecast_origin_utc, run.horizon_id
    ):
        raise ValueError("job key must match forecast run scope and origin")
    if not claim_lease(database_url, subject, key, lease_id, lease_ttl_seconds):
        return WorkerAttempt(None, "not_acquired")
    outcome_id = uuid4()
    try:
        _start_outcome(database_url, subject, key, lease_id, outcome_id)
        result = execute_model_001(database_url=database_url, subject=subject, run=run,
                                   config=config, geometry=geometry, weather_inputs=weather_inputs)
        _finish_outcome(database_url, subject, outcome_id, status="succeeded", run_id=result.run_id,
                        published_points=result.published_points)
        return WorkerAttempt(outcome_id, "succeeded", result.run_id, result.published_points)
    except Exception as error:
        _finish_outcome(database_url, subject, outcome_id, status="failed", error_class=type(error).__name__)
        raise
    finally:
        release_lease(database_url, subject, key, lease_id)
