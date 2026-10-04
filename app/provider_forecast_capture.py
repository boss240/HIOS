"""Immutable source-specific forecast evidence captured before target intervals."""
from datetime import datetime, timezone
import hashlib
import json
import math
import re
from typing import Iterable
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from app.weather_provider_response import ProviderWeatherInterval

_FIELDS = frozenset({
    'temperature_c', 'cloud_cover_pct', 'wind_speed_ms',
    'irradiance_global_wm2', 'irradiance_direct_wm2', 'irradiance_diffuse_wm2',
})
_PROVIDERS = frozenset({'google_weather', 'solcast', 'open_meteo'})


def _utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('capture timestamps must be timezone-aware')
    return value.astimezone(timezone.utc)


def _values(values) -> dict[str, float]:
    result = {}
    for name, value in values.items():
        if name not in _FIELDS:
            raise ValueError('only canonical weather fields may be retained')
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('weather fields must be finite numbers')
        if name != 'temperature_c' and value < 0:
            raise ValueError('weather field is outside its physical range')
        if name == 'cloud_cover_pct' and value > 100:
            raise ValueError('cloud cover must be at most 100')
        result[name] = float(value)
    return result


def capture_document(*, provider: str, mapping_version: str, captured_at: datetime,
                     intervals: Iterable[ProviderWeatherInterval],
                     provider_issued_at: datetime | None = None) -> dict:
    """Freeze parsed future intervals; receipt time never impersonates issue time.

    Raw responses, endpoints, credentials and arbitrary metadata are excluded.
    Callers may select only future intervals before calling this strict boundary.
    """
    if provider not in _PROVIDERS:
        raise ValueError('unsupported forecast provider')
    if not isinstance(mapping_version, str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,80}', mapping_version):
        raise ValueError('mapping version must be a bounded identifier')
    captured = _utc(captured_at)
    issued = None if provider_issued_at is None else _utc(provider_issued_at)
    if issued is not None and issued > captured:
        raise ValueError('provider issue time cannot follow capture time')
    rows = []
    previous_end = None
    for interval in intervals:
        if interval.provider != provider:
            raise ValueError('one capture must contain exactly one provider')
        start, end = _utc(interval.valid_at_utc), _utc(interval.interval_end_utc)
        if start <= captured or end <= start:
            raise ValueError('capture must precede each complete target interval')
        if previous_end is not None and start < previous_end:
            raise ValueError('captured intervals must be ordered and non-overlapping')
        previous_end = end
        values, instant = _values(interval.values), _values(interval.instant_values)
        if not values:
            raise ValueError('each interval requires measured forecast fields')
        if instant:
            sampled = _utc(interval.instant_at_utc)
            if not start <= sampled <= end:
                raise ValueError('instantaneous covariates must belong to their interval')
        elif interval.instant_at_utc is not None:
            raise ValueError('instant sampling time requires instantaneous fields')
        else:
            sampled = None
        rows.append({'start': start.isoformat(), 'end': end.isoformat(),
                     'values': values, 'instant_values': instant,
                     'instant_at': None if sampled is None else sampled.isoformat()})
        if len(rows) > 1000:
            raise ValueError('capture is limited to 1000 intervals')
    if not rows:
        raise ValueError('capture requires future intervals')
    return {'provider': provider, 'mapping_version': mapping_version,
            'captured_at': captured.isoformat(),
            'provider_issued_at': None if issued is None else issued.isoformat(),
            'intervals': rows}


def store_forecast_capture(database_url: str, subject: str, *, capture_id: UUID,
                           tenant_id: str, plant_id: str, provider: str,
                           mapping_version: str, captured_at: datetime,
                           intervals: Iterable[ProviderWeatherInterval],
                           provider_issued_at: datetime | None = None) -> UUID:
    """Persist a validated batch with active membership and plant ownership."""
    document = capture_document(provider=provider, mapping_version=mapping_version,
        captured_at=captured_at, intervals=intervals, provider_issued_at=provider_issued_at)
    digest = hashlib.sha256(json.dumps(document, sort_keys=True, separators=(',', ':'),
        allow_nan=False).encode('utf-8')).hexdigest()
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        allowed = connection.execute('''SELECT 1 FROM plant p JOIN membership m
            ON m.tenant_id=p.tenant_id WHERE p.tenant_id=%s AND p.public_id=%s
            AND m.subject=%s AND m.active''', (tenant_id, plant_id, subject)).fetchone()
        if allowed is None:
            raise PermissionError('active membership and tenant-owned plant required')
        row = connection.execute('''INSERT INTO provider_forecast_capture
            (capture_id,tenant_id,plant_id,provider,mapping_version,captured_at_utc,
             provider_issued_at_utc,document_sha256,document)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (tenant_id,plant_id,document_sha256) DO NOTHING RETURNING capture_id''',
            (capture_id,tenant_id,plant_id,provider,mapping_version,captured_at,
             provider_issued_at,digest,Jsonb(document))).fetchone()
        if row is None:
            row = connection.execute('''SELECT capture_id FROM provider_forecast_capture
                WHERE tenant_id=%s AND plant_id=%s AND document_sha256=%s''',
                (tenant_id,plant_id,digest)).fetchone()
        return row[0]
