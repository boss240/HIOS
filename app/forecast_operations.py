"""Tenant-safe, read-only summaries of controlled forecast-worker outcomes."""
from dataclasses import dataclass
from datetime import datetime, timezone

import psycopg


@dataclass(frozen=True)
class OutcomeSummary:
    tenant_id: str
    plant_id: str
    window_start_utc: datetime
    window_end_utc: datetime
    succeeded: int
    failed: int
    running: int
    published_points: int


def summarize_outcomes(database_url: str, subject: str, tenant_id: str, plant_id: str,
                       window_start: datetime, window_end: datetime) -> OutcomeSummary:
    """Summarize owned-plant attempts; no availability rate is inferred."""
    if window_start.tzinfo is None or window_end.tzinfo is None:
        raise ValueError("outcome window timestamps must be timezone-aware")
    start = window_start.astimezone(timezone.utc)
    end = window_end.astimezone(timezone.utc)
    if end <= start:
        raise ValueError("outcome window_end must be after window_start")
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        row = connection.execute(
            """WITH owned AS (
                    SELECT 1 FROM plant p JOIN membership m ON m.tenant_id=p.tenant_id
                    WHERE p.tenant_id=%s AND p.public_id=%s AND m.subject=%s AND m.active
                ), stats AS (
                    SELECT count(*) FILTER (WHERE status='succeeded'),
                           count(*) FILTER (WHERE status='failed'),
                           count(*) FILTER (WHERE status='running'),
                           coalesce(sum(published_points) FILTER (WHERE status='succeeded'), 0)
                    FROM forecast_job_outcome
                    WHERE tenant_id=%s AND plant_id=%s AND started_at >= %s AND started_at < %s
                      AND EXISTS (SELECT 1 FROM owned)
                ) SELECT EXISTS (SELECT 1 FROM owned), * FROM stats""",
            (tenant_id, plant_id, subject, tenant_id, plant_id, start, end),
        ).fetchone()
        if not row[0]:
            raise PermissionError("Active membership and tenant-owned plant are required")
        return OutcomeSummary(tenant_id, plant_id, start, end, *map(int, row[1:]))
