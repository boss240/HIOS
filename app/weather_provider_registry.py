"""Tenant-safe weather-provider catalogue and metadata-only channel selection."""
from __future__ import annotations

from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class WeatherProviderDefinition:
    key: str
    name: str
    category: str
    summary: str


PROVIDER_CATALOG = {
    "google_weather": WeatherProviderDefinition("google_weather", "Google Weather", "global", "Погода за координатами"),
    "solcast": WeatherProviderDefinition("solcast", "Solcast", "solar", "Сонячна радіація та прогноз генерації"),
    "open_meteo": WeatherProviderDefinition("open_meteo", "Open-Meteo Ensemble", "benchmark", "Ансамблеві сценарії для порівняння"),
    "meteomatics": WeatherProviderDefinition("meteomatics", "Meteomatics", "global", "Високороздільний погодний канал"),
    "meteoblue": WeatherProviderDefinition("meteoblue", "meteoblue", "global", "Мультимодельний погодний прогноз"),
    "eosda_weather": WeatherProviderDefinition("eosda_weather", "EOSDA Weather", "ukrainian", "Український провайдер геопросторових даних"),
    "local_partner": WeatherProviderDefinition("local_partner", "Локальний погодний партнер", "ukrainian", "Контрактний локальний канал"),
}


@dataclass(frozen=True)
class WeatherProviderChannel:
    provider: str
    role: str
    status: str


def _allowed(database_url: str, tenant_id: str, subject: str) -> bool:
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        return connection.execute(
            "SELECT EXISTS(SELECT 1 FROM membership WHERE tenant_id=%s AND subject=%s AND active)",
            (tenant_id, subject),
        ).fetchone()[0]


def list_channels(*, database_url: str, tenant_id: str, subject: str) -> tuple[WeatherProviderChannel, ...]:
    if not _allowed(database_url, tenant_id, subject):
        raise PermissionError("Active membership is required")
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        rows = connection.execute(
            "SELECT provider,role,status FROM weather_provider_channel WHERE tenant_id=%s ORDER BY provider COLLATE \"C\"",
            (tenant_id,),
        ).fetchall()
    return tuple(WeatherProviderChannel(*row) for row in rows)


def configure_channel(*, database_url: str, tenant_id: str, subject: str, provider: str,
                      role: str, status: str = "candidate") -> WeatherProviderChannel:
    if provider not in PROVIDER_CATALOG:
        raise ValueError("provider is not in the approved catalog")
    if role not in {"primary", "challenger", "research"} or status not in {"candidate", "configured", "disabled"}:
        raise ValueError("role or status is invalid")
    if not _allowed(database_url, tenant_id, subject):
        raise PermissionError("Active membership is required")
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        connection.execute(
            """INSERT INTO weather_provider_channel(tenant_id,provider,role,status)
               VALUES (%s,%s,%s,%s)
               ON CONFLICT (tenant_id,provider) DO UPDATE SET role=EXCLUDED.role,status=EXCLUDED.status,updated_at=now()""",
            (tenant_id, provider, role, status),
        )
    return WeatherProviderChannel(provider, role, status)