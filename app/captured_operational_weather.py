"""Read selected immutable captures for one owned plant and forecast origin."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from uuid import UUID
import psycopg
from app.provider_forecast_capture import capture_document
from app.weather_provider_response import ProviderWeatherInterval
from app.operational_weather_composition import compose_hourly_operational_weather, OperationalWeatherInterval


@dataclass(frozen=True)
class CaptureEvidence:
    capture_id: UUID
    document_sha256: str
    document: dict


@dataclass(frozen=True)
class CaptureLineage:
    capture_id: UUID
    provider: str
    mapping_version: str
    document_sha256: str
    captured_at_utc: datetime
    provider_issued_at_utc: datetime | None


@dataclass(frozen=True)
class CapturedOperationalWeather:
    forecast_origin_utc: datetime
    intervals: tuple[OperationalWeatherInterval, ...]
    sources: tuple[CaptureLineage, ...]


def _time(value):
    stamp = datetime.fromisoformat(value) if isinstance(value,str) else value
    if not isinstance(stamp,datetime) or stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError('aware timestamp required')
    return stamp.astimezone(timezone.utc)


def compose_capture_evidence(sources: tuple[CaptureEvidence, ...], *, forecast_origin: datetime) -> CapturedOperationalWeather:
    """Validate checksums and timing; never replace unknown provider issue time."""
    origin = _time(forecast_origin)
    if len(sources) != 2 or len({source.capture_id for source in sources}) != 2:
        raise ValueError('two distinct selected captures required')
    records, lineage = {}, []
    for source in sources:
        if not isinstance(source.capture_id,UUID):raise ValueError('capture UUID required')
        doc=source.document
        digest=hashlib.sha256(json.dumps(doc,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')).hexdigest()
        if digest != source.document_sha256:raise ValueError('capture checksum mismatch')
        provider=doc['provider']
        if provider not in ('google_weather','solcast') or provider in records:
            raise ValueError('one Google and one Solcast capture required')
        captured=_time(doc['captured_at'])
        issued=None if doc['provider_issued_at'] is None else _time(doc['provider_issued_at'])
        if captured > origin:raise ValueError('capture was received after forecast origin')
        rows=tuple(ProviderWeatherInterval(provider,_time(row['start']),_time(row['end']),
            row['values'],row['instant_values'],None if row['instant_at'] is None else _time(row['instant_at']))
            for row in doc['intervals'])
        validated=capture_document(provider=provider,mapping_version=doc['mapping_version'],
            captured_at=captured,provider_issued_at=issued,intervals=rows)
        if validated != doc:raise ValueError('capture document is not canonical')
        # A replay origin may be later than receipt; started intervals never enter
        # its forecast inputs. The paired selected source IDs remain unchanged.
        records[provider]=tuple(row for row in rows if row.valid_at_utc > origin)
        lineage.append(CaptureLineage(source.capture_id,provider,doc['mapping_version'],digest,captured,issued))
    intervals=compose_hourly_operational_weather(google=records['google_weather'],solcast=records['solcast'])
    return CapturedOperationalWeather(origin,intervals,tuple(sorted(lineage,key=lambda s:s.provider)))


def load_captured_operational_weather(database_url: str, subject: str, *, tenant_id: str,
        plant_id: str, capture_ids: tuple[UUID, UUID], forecast_origin: datetime) -> CapturedOperationalWeather:
    """One tenant-filtered read, with active membership checked in the query.

    IDs must be supplied explicitly; latest captures are never silently chosen
    for a historical origin. This reader writes nothing and makes no API calls.
    """
    if not isinstance(capture_ids,tuple) or len(capture_ids)!=2 or len(set(capture_ids))!=2 or any(not isinstance(id,UUID) for id in capture_ids):
        raise ValueError('two distinct capture UUIDs required')
    with psycopg.connect(database_url,connect_timeout=5) as connection:
        rows=connection.execute('''SELECT c.capture_id,c.document_sha256,c.document
            FROM provider_forecast_capture c JOIN plant p
              ON p.public_id=c.plant_id AND p.tenant_id=c.tenant_id
            WHERE c.tenant_id=%s AND c.plant_id=%s AND c.capture_id=ANY(%s)
              AND EXISTS (SELECT 1 FROM membership m WHERE m.tenant_id=c.tenant_id
                AND m.subject=%s AND m.active)''',
            (tenant_id,plant_id,list(capture_ids),subject)).fetchall()
    if len(rows)!=2:raise PermissionError('selected captures must belong to an actively owned plant')
    return compose_capture_evidence(tuple(CaptureEvidence(*row) for row in rows),forecast_origin=forecast_origin)
