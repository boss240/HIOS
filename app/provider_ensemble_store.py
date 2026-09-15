"""Tenant-safe persistence for the latest per-plant provider ensemble profile."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import psycopg

from app.provider_ensemble import EnsembleProfile, ProviderScore


@dataclass(frozen=True)
class StoredProviderScore:
    provider: str
    pair_count: int
    mae_kw: float
    bias_kw: float
    correlation: float | None
    weight: float
    calibrated_at_utc: datetime


def replace_profile(*, database_url: str, subject: str, tenant_id: str,
                    profile: EnsembleProfile, calibrated_at_utc: datetime) -> None:
    """Atomically replace a plant's derived profile after ownership verification."""
    if calibrated_at_utc.tzinfo is None:
        raise ValueError("calibrated_at_utc must include a timezone")
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        row = connection.execute(
            """SELECT EXISTS(
                   SELECT 1 FROM plant p JOIN membership m ON m.tenant_id = p.tenant_id
                   WHERE p.tenant_id=%s AND p.public_id=%s AND m.subject=%s AND m.active
                )""",
            (tenant_id, profile.plant_key, subject),
        ).fetchone()
        if not row[0]:
            raise PermissionError("Active membership and tenant-owned plant are required")
        connection.execute(
            "DELETE FROM provider_ensemble_profile WHERE tenant_id=%s AND plant_id=%s",
            (tenant_id, profile.plant_key),
        )
        connection.executemany(
            """INSERT INTO provider_ensemble_profile(
                   tenant_id, plant_id, provider, pair_count, mae_kw, bias_kw, correlation,
                   weight, calibrated_at_utc
               ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            [(tenant_id, profile.plant_key, score.provider, score.pair_count, score.mae_kw,
              score.bias_kw, score.correlation, score.weight, calibrated_at_utc)
             for score in profile.scores],
        )


def load_profile(*, database_url: str, subject: str, tenant_id: str,
                 plant_id: str) -> tuple[StoredProviderScore, ...]:
    """Return a tenant-authorized plant profile, ordered deterministically by provider."""
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        rows = connection.execute(
            """SELECT e.provider, e.pair_count, e.mae_kw, e.bias_kw, e.correlation, e.weight,
                      e.calibrated_at_utc
               FROM provider_ensemble_profile e JOIN membership m ON m.tenant_id=e.tenant_id
               WHERE e.tenant_id=%s AND e.plant_id=%s AND m.subject=%s AND m.active
               ORDER BY e.provider COLLATE \"C\"""",
            (tenant_id, plant_id, subject),
        ).fetchall()
        owned = connection.execute(
            """SELECT EXISTS(
                   SELECT 1 FROM plant p JOIN membership m ON m.tenant_id=p.tenant_id
                   WHERE p.tenant_id=%s AND p.public_id=%s AND m.subject=%s AND m.active
                )""", (tenant_id, plant_id, subject),
        ).fetchone()
    if not owned[0]:
        raise PermissionError("Active membership and tenant-owned plant are required")
    return tuple(StoredProviderScore(*row) for row in rows)
