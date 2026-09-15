"""Tenant-safe requests to start read-only inverter-cloud onboarding."""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import psycopg

from app.inverter_cloud import InverterCloudProvider


@dataclass(frozen=True)
class CloudConnectionRequest:
    request_id: UUID
    plant_id: str
    provider: str
    status: str
    external_plant_id: str | None = None


def request_connection(*, database_url: str, tenant_id: str, subject: str, plant_id: str,
                       provider: InverterCloudProvider, external_plant_id: str | None = None) -> CloudConnectionRequest:
    """Record consent-free pre-discovery intent. Credentials and native IDs are excluded."""
    if external_plant_id is not None and (not isinstance(external_plant_id, str) or not (external_plant_id := external_plant_id.strip())):
        raise ValueError("external_plant_id must be non-empty when supplied")
    request_id = uuid4()
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        owned = connection.execute(
            """SELECT EXISTS(SELECT 1 FROM plant p JOIN membership m ON m.tenant_id=p.tenant_id
               WHERE p.tenant_id=%s AND p.public_id=%s AND m.subject=%s AND m.active)""",
            (tenant_id, plant_id, subject),
        ).fetchone()[0]
        if not owned:
            raise PermissionError("Active membership and tenant-owned plant are required")
        row = connection.execute(
            """INSERT INTO inverter_cloud_connection_request(request_id,tenant_id,plant_id,provider,external_plant_id)
               VALUES (%s,%s,%s,%s,%s)
               ON CONFLICT (tenant_id,plant_id,provider) DO UPDATE SET external_plant_id=COALESCE(EXCLUDED.external_plant_id,inverter_cloud_connection_request.external_plant_id),updated_at=now()
               RETURNING request_id,plant_id,provider,status,external_plant_id""",
            (request_id, tenant_id, plant_id, provider.value, external_plant_id),
        ).fetchone()
    return CloudConnectionRequest(*row)


def list_connection_requests(*, database_url: str, tenant_id: str, subject: str,
                             plant_id: str) -> tuple[CloudConnectionRequest, ...]:
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        owned = connection.execute(
            """SELECT EXISTS(SELECT 1 FROM plant p JOIN membership m ON m.tenant_id=p.tenant_id
               WHERE p.tenant_id=%s AND p.public_id=%s AND m.subject=%s AND m.active)""",
            (tenant_id, plant_id, subject),
        ).fetchone()[0]
        if not owned:
            raise PermissionError("Active membership and tenant-owned plant are required")
        rows = connection.execute(
            """SELECT request_id,plant_id,provider,status,external_plant_id FROM inverter_cloud_connection_request
               WHERE tenant_id=%s AND plant_id=%s ORDER BY provider COLLATE \"C\"""",
            (tenant_id, plant_id),
        ).fetchall()
    return tuple(CloudConnectionRequest(*row) for row in rows)