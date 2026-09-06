"""UTC schedule calculations and PostgreSQL leases for future forecast workers."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

import psycopg


@dataclass(frozen=True)
class ScheduleSpec:
    horizon_id: str
    cadence_minutes: int = 60
    publication_delay_minutes: int = 0

    def __post_init__(self) -> None:
        if self.horizon_id not in ("intraday", "day_ahead"):
            raise ValueError("horizon_id must be intraday or day_ahead")
        if self.cadence_minutes < 1 or 1440 % self.cadence_minutes:
            raise ValueError("cadence_minutes must divide one UTC day")
        if self.publication_delay_minutes < 0:
            raise ValueError("publication_delay_minutes must not be negative")


@dataclass(frozen=True)
class JobKey:
    tenant_id: str
    plant_id: str
    forecast_origin_utc: datetime
    horizon_id: str


def latest_due_origin(now: datetime, spec: ScheduleSpec) -> datetime:
    """Return the latest UTC-aligned origin eligible after the configured delay."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    eligible = now.astimezone(timezone.utc) - timedelta(minutes=spec.publication_delay_minutes)
    day_start = eligible.replace(hour=0, minute=0, second=0, microsecond=0)
    elapsed_minutes = int((eligible - day_start).total_seconds() // 60)
    return day_start + timedelta(minutes=elapsed_minutes - elapsed_minutes % spec.cadence_minutes)


def claim_lease(database_url: str, subject: str, key: JobKey, lease_id: UUID,
                ttl_seconds: int = 300) -> bool:
    """Claim or renew this lease only for an active member and owned plant."""
    if ttl_seconds < 1:
        raise ValueError("ttl_seconds must be positive")
    if key.forecast_origin_utc.tzinfo is None or key.forecast_origin_utc.utcoffset() is None:
        raise ValueError("forecast_origin_utc must be timezone-aware")
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        row = connection.execute(
            """WITH owned AS (
                    SELECT 1 FROM plant p JOIN membership m ON m.tenant_id = p.tenant_id
                    WHERE p.tenant_id=%s AND p.public_id=%s AND m.subject=%s AND m.active
                ), claimed AS (
                    INSERT INTO forecast_job_lease (
                        tenant_id, plant_id, forecast_origin_utc, horizon_id, lease_id, claimed_by, expires_at
                    ) SELECT %s, %s, %s, %s, %s, %s, now() + (%s * interval '1 second') FROM owned
                    ON CONFLICT (tenant_id, plant_id, forecast_origin_utc, horizon_id) DO UPDATE
                    SET lease_id=EXCLUDED.lease_id, claimed_by=EXCLUDED.claimed_by, expires_at=EXCLUDED.expires_at,
                        claimed_at=now()
                    WHERE forecast_job_lease.expires_at <= now() OR forecast_job_lease.lease_id=EXCLUDED.lease_id
                    RETURNING lease_id
                ) SELECT EXISTS (SELECT 1 FROM owned), (SELECT lease_id FROM claimed)""",
            (key.tenant_id, key.plant_id, subject, key.tenant_id, key.plant_id,
             key.forecast_origin_utc, key.horizon_id, lease_id, subject, ttl_seconds),
        ).fetchone()
        if not row[0]:
            raise PermissionError("Active membership and tenant-owned plant are required")
        return row[1] == lease_id


def release_lease(database_url: str, subject: str, key: JobKey, lease_id: UUID) -> bool:
    """Release only the caller's currently held lease in the same tenant scope."""
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        row = connection.execute(
            """WITH owned AS (
                    SELECT 1 FROM plant p JOIN membership m ON m.tenant_id = p.tenant_id
                    WHERE p.tenant_id=%s AND p.public_id=%s AND m.subject=%s AND m.active
                ), deleted AS (
                    DELETE FROM forecast_job_lease l USING owned
                    WHERE l.tenant_id=%s AND l.plant_id=%s AND l.forecast_origin_utc=%s
                      AND l.horizon_id=%s AND l.lease_id=%s AND l.claimed_by=%s
                    RETURNING 1
                ) SELECT EXISTS (SELECT 1 FROM owned), EXISTS (SELECT 1 FROM deleted)""",
            (key.tenant_id, key.plant_id, subject, key.tenant_id, key.plant_id,
             key.forecast_origin_utc, key.horizon_id, lease_id, subject),
        ).fetchone()
        if not row[0]:
            raise PermissionError("Active membership and tenant-owned plant are required")
        return row[1]
