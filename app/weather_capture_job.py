"""Bounded Azure job entrypoint for explicitly scoped forecast capture."""
from datetime import datetime, timezone
import hashlib
import json
import os
import sys
import psycopg
from app.provider_forecast_collection import collect_provider_forecast
from app.weather_provider_clients import WeatherProviderHttpError


def plant_scope(value: str) -> tuple[str, ...]:
    try:
        plants = json.loads(value)
    except (TypeError, ValueError) as error:
        raise ValueError('plant scope must be JSON') from error
    if (not isinstance(plants,list) or not 1 <= len(plants) <= 2
        or any(not isinstance(p,str) or not p.strip() or len(p)>120 for p in plants)
        or len(set(plants)) != len(plants)):
        raise ValueError('one or two distinct plant IDs are required')
    return tuple(plants)


def run_capture_job(*, database_url: str, subject: str, tenant_id: str,
                    plant_ids: tuple[str,...], collector=None, now=None) -> tuple[dict,...]:
    """Try each plant/source once; serialize duplicates and skip captured slots.

    A slot is one half-day in UTC. Existing successful captures satisfy it.
    Partial failure does not erase another source and does not trigger retries.
    Provider errors are represented only by class, never response or URL text.
    """
    plant_scope(json.dumps(list(plant_ids)))
    if not subject or not tenant_id:
        raise ValueError('operator scope is required')
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError('job clock must be timezone-aware')
    current = current.astimezone(timezone.utc)
    slot = current.replace(hour=0 if current.hour<12 else 12,minute=0,second=0,microsecond=0)
    collect = collector or collect_provider_forecast
    outcomes=[]
    for index,plant_id in enumerate(plant_ids):
        for provider in ('google_weather','solcast'):
            public = {'plantIndex':index,'provider':provider}
            try:
                with psycopg.connect(database_url,connect_timeout=5) as connection:
                    allowed=connection.execute('''SELECT 1 FROM plant p JOIN membership m
                        ON m.tenant_id=p.tenant_id WHERE p.tenant_id=%s AND p.public_id=%s
                        AND m.subject=%s AND m.active''',(tenant_id,plant_id,subject)).fetchone()
                    if allowed is None:
                        raise PermissionError('job plant is not authorised')
                    key=int.from_bytes(hashlib.sha256(json.dumps([tenant_id,plant_id,provider]).encode()).digest()[:8], 'big',signed=True)
                    held=connection.execute('SELECT pg_try_advisory_lock(%s)',(key,)).fetchone()[0]
                    if not held:
                        outcomes.append({**public,'status':'already_running'});continue
                    existing=connection.execute('''SELECT 1 FROM provider_forecast_capture
                        WHERE tenant_id=%s AND plant_id=%s AND provider=%s
                        AND captured_at_utc >= %s LIMIT 1''',(tenant_id,plant_id,provider,slot)).fetchone()
                    if existing:
                        outcomes.append({**public,'status':'slot_already_captured'});continue
                    result=collect(database_url,subject,tenant_id=tenant_id,plant_id=plant_id,provider=provider)
                    outcomes.append({**public,'status':'captured','intervalCount':result['intervalCount']})
            except Exception as error:
                failure={**public,'status':'failed','errorClass':type(error).__name__}
                if isinstance(error, WeatherProviderHttpError):
                    failure['errorCode']=error.public_code
                outcomes.append(failure)
    return tuple(outcomes)


def main() -> int:
    try:
        outcomes=run_capture_job(database_url=os.environ['DATABASE_URL'],
            subject=os.environ['HIOS_CAPTURE_SUBJECT'],tenant_id=os.environ['HIOS_CAPTURE_TENANT'],
            plant_ids=plant_scope(os.environ['HIOS_CAPTURE_PLANTS']))
        print(json.dumps({'outcomes':outcomes}))
        return 1 if any(o['status']=='failed' for o in outcomes) else 0
    except Exception as error:
        print(json.dumps({'status':'configuration_failed','errorClass':type(error).__name__}))
        return 2


if __name__=='__main__':
    sys.exit(main())
