"""Tenant-safe persistence of normalized weather intervals; no provider network client."""
from dataclasses import dataclass
from uuid import UUID

import psycopg

from app.weather_normalization import NormalizedWeather


@dataclass(frozen=True)
class WeatherSnapshot:
    snapshot_id: UUID
    tenant_id: str
    plant_id: str
    source_reference: str
    payload_sha256: str
    weather: NormalizedWeather


def create_or_get_snapshot(database_url: str, subject: str, snapshot: WeatherSnapshot) -> UUID:
    """Store a normalized weather interval once after membership and plant checks."""
    weather = snapshot.weather
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
                    INSERT INTO weather_snapshot (
                        snapshot_id, tenant_id, plant_id, provider, product, mapping_version,
                        provider_issued_at_utc, valid_at_utc, interval_end_utc, retrieved_at_utc,
                        source_reference, payload_sha256, irradiance_global_wm2, cloud_cover_pct,
                        temperature_c, wind_speed_ms, irradiance_direct_wm2,
                        irradiance_diffuse_wm2, relative_humidity_pct, precipitation_mm
                    )
                    SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                           %s, %s, %s, %s, %s, %s, %s, %s
                    FROM owned_plant
                    ON CONFLICT (tenant_id, plant_id, provider, product, mapping_version,
                                 provider_issued_at_utc, valid_at_utc, payload_sha256) DO NOTHING
                    RETURNING snapshot_id
                )
                SELECT snapshot_id FROM inserted
                UNION ALL
                SELECT w.snapshot_id FROM weather_snapshot w
                WHERE w.tenant_id = %s AND w.plant_id = %s AND w.provider = %s
                  AND w.product = %s AND w.mapping_version = %s
                  AND w.provider_issued_at_utc = %s AND w.valid_at_utc = %s
                  AND w.payload_sha256 = %s AND EXISTS (SELECT 1 FROM owned_plant)
                LIMIT 1""",
            (snapshot.tenant_id, subject, snapshot.tenant_id, snapshot.plant_id,
             snapshot.snapshot_id, snapshot.tenant_id, snapshot.plant_id,
             weather.provider, weather.product, weather.mapping_version,
             weather.provider_issued_at_utc, weather.valid_at_utc, weather.interval_end_utc,
             weather.retrieved_at_utc, snapshot.source_reference, snapshot.payload_sha256,
             weather.irradiance_global_wm2, weather.cloud_cover_pct, weather.temperature_c,
             weather.wind_speed_ms, weather.irradiance_direct_wm2,
             weather.irradiance_diffuse_wm2, weather.relative_humidity_pct,
             weather.precipitation_mm, snapshot.tenant_id, snapshot.plant_id,
             weather.provider, weather.product, weather.mapping_version,
             weather.provider_issued_at_utc, weather.valid_at_utc, snapshot.payload_sha256),
        ).fetchone()
        if row is None:
            raise PermissionError("Active membership and tenant-owned plant are required")
        return row[0]
