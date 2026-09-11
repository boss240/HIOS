"""Tenant-safe persistence of normalized measured generation; no provider client."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
import re
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from app.actuals_field_mapping import EnergySemantics


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


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


def _measurement(value: float | None, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative number when supplied")
    return float(value)


@dataclass(frozen=True)
class ActualGenerationObservation:
    provider: str
    mapping_version: str
    observed_at_utc: datetime
    interval_end_utc: datetime
    retrieved_at_utc: datetime
    ac_power_kw: float | None
    energy_kwh: float | None
    energy_semantics: EnergySemantics | None = None
    device_status: str | None = None
    quality_flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _name(self.provider, "provider")
        _name(self.mapping_version, "mapping_version")
        observed = _utc(self.observed_at_utc, "observed_at_utc")
        interval_end = _utc(self.interval_end_utc, "interval_end_utc")
        retrieved = _utc(self.retrieved_at_utc, "retrieved_at_utc")
        if interval_end <= observed:
            raise ValueError("interval_end_utc must be after observed_at_utc")
        if retrieved < observed:
            raise ValueError("retrieved_at_utc must not be before observed_at_utc")
        power = _measurement(self.ac_power_kw, "ac_power_kw")
        energy = _measurement(self.energy_kwh, "energy_kwh")
        if power is None and energy is None:
            raise ValueError("at least one measured value is required")
        if energy is None and self.energy_semantics is not None:
            raise ValueError("energy_semantics requires energy_kwh")
        if energy is not None and not isinstance(self.energy_semantics, EnergySemantics):
            raise ValueError("energy_semantics is required when energy_kwh is supplied")
        if self.device_status is not None:
            _name(self.device_status, "device_status")
        if any(not isinstance(flag, str) or not flag.strip() for flag in self.quality_flags):
            raise ValueError("quality_flags must contain non-empty strings")


@dataclass(frozen=True)
class ActualGenerationSnapshot:
    snapshot_id: UUID
    tenant_id: str
    plant_id: str
    source_reference: str
    payload_sha256: str
    observation: ActualGenerationObservation

    def __post_init__(self) -> None:
        _name(self.tenant_id, "tenant_id")
        _name(self.plant_id, "plant_id")
        _name(self.source_reference, "source_reference")
        if not isinstance(self.payload_sha256, str) or not _SHA256.fullmatch(self.payload_sha256):
            raise ValueError("payload_sha256 must be a lowercase SHA-256 hex digest")


def create_or_get_actual_snapshot(database_url: str, subject: str,
                                  snapshot: ActualGenerationSnapshot) -> UUID:
    """Store one normalized actual once after membership and plant ownership checks."""
    observation = snapshot.observation
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
                    INSERT INTO actual_generation_snapshot (
                        snapshot_id, tenant_id, plant_id, provider, mapping_version,
                        observed_at_utc, interval_end_utc, retrieved_at_utc,
                        source_reference, payload_sha256, ac_power_kw, energy_kwh, energy_semantics,
                        device_status, quality_flags
                    ) SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    FROM owned_plant
                    ON CONFLICT (tenant_id, plant_id, provider, mapping_version,
                                 observed_at_utc, interval_end_utc, payload_sha256) DO NOTHING
                    RETURNING snapshot_id
                ) SELECT snapshot_id FROM inserted
                UNION ALL
                SELECT a.snapshot_id FROM actual_generation_snapshot a
                WHERE a.tenant_id = %s AND a.plant_id = %s AND a.provider = %s
                  AND a.mapping_version = %s AND a.observed_at_utc = %s
                  AND a.interval_end_utc = %s AND a.payload_sha256 = %s
                  AND EXISTS (SELECT 1 FROM owned_plant)
                LIMIT 1""",
            (
                snapshot.tenant_id, subject, snapshot.tenant_id, snapshot.plant_id,
                snapshot.snapshot_id, snapshot.tenant_id, snapshot.plant_id,
                observation.provider, observation.mapping_version,
                observation.observed_at_utc, observation.interval_end_utc,
                observation.retrieved_at_utc, snapshot.source_reference, snapshot.payload_sha256,
                observation.ac_power_kw, observation.energy_kwh,
                observation.energy_semantics.value if observation.energy_semantics else None,
                observation.device_status,
                Jsonb(list(observation.quality_flags)),
                snapshot.tenant_id, snapshot.plant_id, observation.provider,
                observation.mapping_version, observation.observed_at_utc,
                observation.interval_end_utc, snapshot.payload_sha256,
            ),
        ).fetchone()
        if row is None:
            raise PermissionError("Active membership and tenant-owned plant are required")
        return row[0]
