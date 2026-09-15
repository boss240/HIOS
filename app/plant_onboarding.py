"""Tenant-safe onboarding for a plant and its read-only inverter-cloud bindings."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

import psycopg

from app.inverter_cloud import InverterCloudBinding, InverterCloudProvider


@dataclass(frozen=True)
class PlantProfileInput:
    latitude: float | None = None
    longitude: float | None = None
    timezone_name: str | None = None
    capacity_ac_kw: float | None = None
    tilt_deg: float | None = None
    azimuth_deg: float | None = None
    mounting_type: str | None = None
    meter_boundary: str | None = None
    commissioning_date: date | None = None
    operator_notes: str | None = None


def _clean(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not (result := value.strip()):
        raise ValueError(f"{field} must be a non-empty string when supplied")
    return result


def _finite(value: float | None, field: str, lower: float, upper: float) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not lower <= value <= upper:
        raise ValueError(f"{field} is outside its allowed range")
    return float(value)


def validate_profile(profile: PlantProfileInput) -> PlantProfileInput:
    latitude = _finite(profile.latitude, "latitude", -90, 90)
    longitude = _finite(profile.longitude, "longitude", -180, 180)
    return PlantProfileInput(
        latitude=latitude, longitude=longitude,
        timezone_name=_clean(profile.timezone_name, "timezone_name"),
        capacity_ac_kw=_finite(profile.capacity_ac_kw, "capacity_ac_kw", 0, 1_000_000),
        tilt_deg=_finite(profile.tilt_deg, "tilt_deg", 0, 90),
        azimuth_deg=_finite(profile.azimuth_deg, "azimuth_deg", 0, 359.999999),
        mounting_type=_clean(profile.mounting_type, "mounting_type"),
        meter_boundary=_clean(profile.meter_boundary, "meter_boundary"),
        commissioning_date=profile.commissioning_date,
        operator_notes=_clean(profile.operator_notes, "operator_notes"),
    )


def create_plant(*, database_url: str, subject: str, tenant_id: str, name: str,
                 capacity_kw: float | None, profile: PlantProfileInput) -> str:
    """Create one tenant-owned plant; this only records operator-entered passport data."""
    name = _clean(name, "name")
    capacity_kw = _finite(capacity_kw, "capacity_kw", 0, 1_000_000)
    profile = validate_profile(profile)
    plant_id = "plant-" + uuid4().hex
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        allowed = connection.execute(
            "SELECT EXISTS(SELECT 1 FROM membership WHERE tenant_id=%s AND subject=%s AND active)",
            (tenant_id, subject),
        ).fetchone()[0]
        if not allowed:
            raise PermissionError("Active membership is required")
        connection.execute(
            "INSERT INTO plant(public_id, tenant_id, name, capacity_kw) VALUES (%s,%s,%s,%s)",
            (plant_id, tenant_id, name, capacity_kw),
        )
        connection.execute(
            """INSERT INTO plant_profile(plant_id,latitude,longitude,timezone_name,capacity_ac_kw,
                   tilt_deg,azimuth_deg,mounting_type,meter_boundary,commissioning_date,operator_notes)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (plant_id, profile.latitude, profile.longitude, profile.timezone_name, profile.capacity_ac_kw,
             profile.tilt_deg, profile.azimuth_deg, profile.mounting_type, profile.meter_boundary,
             profile.commissioning_date, profile.operator_notes),
        )
    return plant_id


def add_read_only_binding(*, database_url: str, subject: str, binding: InverterCloudBinding,
                          discovery_status: str = "pending") -> UUID:
    """Register an approved secret reference and discovered native plant ID without a secret value."""
    if discovery_status not in {"pending", "verified", "blocked"}:
        raise ValueError("discovery_status is invalid")
    binding_id = uuid4()
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        owned = connection.execute(
            """SELECT EXISTS(SELECT 1 FROM plant p JOIN membership m ON m.tenant_id=p.tenant_id
               WHERE p.tenant_id=%s AND p.public_id=%s AND m.subject=%s AND m.active)""",
            (binding.tenant_id, binding.plant_id, subject),
        ).fetchone()[0]
        if not owned:
            raise PermissionError("Active membership and tenant-owned plant are required")
        connection.execute(
            """INSERT INTO inverter_cloud_binding(binding_id,tenant_id,plant_id,provider,external_plant_id,
                   credential_reference,consent_record_reference,mapping_version,read_only,discovery_status)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,true,%s)""",
            (binding_id, binding.tenant_id, binding.plant_id, binding.provider.value,
             binding.external_plant_id, binding.credential_reference, binding.consent_record_reference,
             binding.mapping_version, discovery_status),
        )
    return binding_id


def get_onboarding(*, database_url: str, subject: str, tenant_id: str, plant_id: str) -> dict:
    """Return owner-visible manual profile and metadata-only cloud bindings."""
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        row = connection.execute(
            """SELECT p.public_id,p.name,p.capacity_kw,pp.latitude,pp.longitude,pp.timezone_name,pp.capacity_ac_kw,
                      pp.tilt_deg,pp.azimuth_deg,pp.mounting_type,pp.meter_boundary,pp.commissioning_date,pp.operator_notes
               FROM plant p JOIN membership m ON m.tenant_id=p.tenant_id LEFT JOIN plant_profile pp ON pp.plant_id=p.public_id
               WHERE p.tenant_id=%s AND p.public_id=%s AND m.subject=%s AND m.active""",
            (tenant_id, plant_id, subject),
        ).fetchone()
        if row is None:
            raise PermissionError("Active membership and tenant-owned plant are required")
        bindings = connection.execute(
            """SELECT provider,external_plant_id,credential_reference,consent_record_reference,mapping_version,
                      read_only,discovery_status FROM inverter_cloud_binding
               WHERE tenant_id=%s AND plant_id=%s ORDER BY provider COLLATE \"C\", external_plant_id COLLATE \"C\"""",
            (tenant_id, plant_id),
        ).fetchall()
    keys = ("id", "name", "capacityKw", "latitude", "longitude", "timezone", "capacityAcKw", "tiltDeg", "azimuthDeg", "mountingType", "meterBoundary", "commissioningDate", "operatorNotes")
    data = {key: value for key, value in zip(keys, row) if value is not None}
    data["cloudBindings"] = [dict(zip(("provider", "externalPlantId", "credentialReference", "consentRecordReference", "mappingVersion", "readOnly", "discoveryStatus"), value)) for value in bindings]
    return data