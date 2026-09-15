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


def request_connection(*, database_url: str, tenant_id: str, subject: str, plant_id: str,
                       provider: InverterCloudProvider) -> CloudConnectionRequest:
    """Record consent-free pre-discovery intent. Credentials and native IDs are excluded."""
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
            """INSERT INTO inverter_cloud_connection_request(request_id,tenant_id,plant_id,provider)
               VALUES (%s,%s,%s,%s)
               ON CONFLICT (tenant_id,plant_id,provider) DO UPDATE SET updated_at=now()
               RETURNING request_id,plant_id,provider,status""",
            (request_id, tenant_id, plant_id, provider.value),
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
            """SELECT request_id,plant_id,provider,status FROM inverter_cloud_connection_request
               WHERE tenant_id=%s AND plant_id=%s ORDER BY provider COLLATE \"C\"""",
            (tenant_id, plant_id),
        ).fetchall()
    return tuple(CloudConnectionRequest(*row) for row in rows)