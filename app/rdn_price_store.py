"""Tenant-scoped, auditable RDN price scenarios. No live market feed or trading action."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
from uuid import UUID, uuid4

import psycopg


@dataclass(frozen=True)
class RdnPricePoint:
    interval_start_utc: datetime
    price_uah_per_kwh: float


def _point(raw: dict) -> RdnPricePoint:
    if not isinstance(raw, dict):
        raise ValueError("each price point must be an object")
    value = raw.get("priceUahPerKwh")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError("priceUahPerKwh must be a finite non-negative number")
    timestamp = raw.get("intervalStartUtc")
    if not isinstance(timestamp, str):
        raise ValueError("intervalStartUtc must be an ISO timestamp")
    try:
        start = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("intervalStartUtc must be an ISO timestamp") from error
    if start.tzinfo is None:
        raise ValueError("intervalStartUtc must include a timezone")
    return RdnPricePoint(start, float(value))


def create_scenario(database_url: str, tenant_id: str, subject: str, name: str,
                    points: list[dict], source_reference: str | None = None) -> UUID:
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
        raise ValueError("name must contain 1 to 120 characters")
    parsed = tuple(_point(item) for item in points)
    if not 1 <= len(parsed) <= 744 or len({item.interval_start_utc for item in parsed}) != len(parsed):
        raise ValueError("points must contain 1 to 744 unique intervals")
    if source_reference is not None and (not isinstance(source_reference, str) or len(source_reference.strip()) > 500):
        raise ValueError("sourceReference is invalid")
    scenario_id = uuid4()
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        allowed = connection.execute("SELECT 1 FROM membership WHERE tenant_id=%s AND subject=%s AND active", (tenant_id, subject)).fetchone()
        if allowed is None:
            raise PermissionError("active membership required")
        connection.execute("INSERT INTO rdn_price_scenario(scenario_id,tenant_id,name,source_reference) VALUES (%s,%s,%s,%s)",
                           (scenario_id, tenant_id, name.strip(), source_reference.strip() if source_reference else None))
        connection.executemany("INSERT INTO rdn_price_point(scenario_id,interval_start_utc,price_uah_per_kwh) VALUES (%s,%s,%s)",
                               [(scenario_id, item.interval_start_utc, item.price_uah_per_kwh) for item in parsed])
    return scenario_id


def list_scenarios(database_url: str, tenant_id: str, subject: str) -> list[dict]:
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        rows = connection.execute("""SELECT s.scenario_id,s.name,s.source_reference,s.created_at,count(p.*)
            FROM rdn_price_scenario s JOIN membership m ON m.tenant_id=s.tenant_id
            LEFT JOIN rdn_price_point p ON p.scenario_id=s.scenario_id
            WHERE s.tenant_id=%s AND m.subject=%s AND m.active
            GROUP BY s.scenario_id ORDER BY s.created_at DESC""", (tenant_id, subject)).fetchall()
    return [{"id": str(row[0]), "name": row[1], "sourceReference": row[2], "createdAt": row[3], "pointCount": row[4]} for row in rows]


def scenario_prices_for_intervals(database_url: str, tenant_id: str, subject: str, scenario_id: str,
                                  starts: tuple[datetime, ...]) -> list[float]:
    try:
        scenario_uuid = UUID(scenario_id)
    except (TypeError, ValueError) as error:
        raise ValueError("rdnScenarioId is invalid") from error
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        rows = connection.execute("""SELECT p.interval_start_utc,p.price_uah_per_kwh
            FROM rdn_price_point p JOIN rdn_price_scenario s ON s.scenario_id=p.scenario_id
            JOIN membership m ON m.tenant_id=s.tenant_id
            WHERE s.scenario_id=%s AND s.tenant_id=%s AND m.subject=%s AND m.active
            ORDER BY p.interval_start_utc""", (scenario_uuid, tenant_id, subject)).fetchall()
    prices = {row[0]: float(row[1]) for row in rows}
    if len(prices) != len(starts) or any(start not in prices for start in starts):
        raise ValueError("RDN scenario does not cover every forecast interval")
    return [prices[start] for start in starts]
