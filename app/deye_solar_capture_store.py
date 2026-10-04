"""Persist device PV evidence separately from verified plant AC actuals."""
from datetime import date, datetime, timezone
from hashlib import sha256
import json
from uuid import uuid4
import psycopg
from psycopg.types.json import Jsonb
from app.deye_solar_history import solar_power_samples, solar_hourly_preview


def store_device_solar_capture(database_url, subject, *, tenant_id, plant_id,
                               device_serial, day, retrieved_at, body):
    if (not isinstance(device_serial, str) or not device_serial.strip()
            or device_serial != device_serial.strip() or len(device_serial)>128):
        raise ValueError('selected device serial required')
    if not isinstance(body, dict) or body.get('deviceSn') != device_serial:
        raise ValueError('history must match selected device')
    if (not isinstance(retrieved_at, datetime) or retrieved_at.tzinfo is None
            or retrieved_at.utcoffset() is None):
        raise ValueError('aware receipt required')
    receipt = retrieved_at.astimezone(timezone.utc)
    if isinstance(day, datetime) or not isinstance(day, date) or day >= receipt.date():
        raise ValueError('completed UTC day required')
    samples = solar_power_samples(body)
    if not samples or len(samples)>1000 or not any(s['generationPower'] is not None for s in samples):
        raise ValueError('bounded history with measured solar power required')
    document = {'mappingVersion':'deye-device-solar-v1', 'dayUtc':day.isoformat(),
                'field':'TotalSolarPower', 'unit':'W', 'scope':'device_only',
                'samples':samples,
                'hours':solar_hourly_preview(body, day=day)}
    origin = int(datetime.combine(day, datetime.min.time(), timezone.utc).timestamp())
    if any(not origin <= s['timeStamp'] < origin+86400 for s in samples):
        raise ValueError('samples must belong to requested UTC day')
    digest = sha256(json.dumps(document, sort_keys=True, separators=(',', ':'),
                              allow_nan=False).encode()).hexdigest()
    device_hash = sha256(device_serial.encode()).hexdigest()
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        allowed = connection.execute('''SELECT 1 FROM plant p JOIN membership m
            ON m.tenant_id=p.tenant_id WHERE p.tenant_id=%s AND p.public_id=%s
            AND m.subject=%s AND m.active FOR SHARE OF p,m''',
            (tenant_id,plant_id,subject)).fetchone()
        if allowed is None:
            raise PermissionError('active membership and owned plant required')
        row = connection.execute('''INSERT INTO device_solar_capture
            (capture_id,tenant_id,plant_id,device_sha256,day_utc,retrieved_at_utc,
             document_sha256,document) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT(tenant_id,plant_id,device_sha256,day_utc,document_sha256)
            DO NOTHING RETURNING capture_id''', (uuid4(),tenant_id,plant_id,
                device_hash,day,receipt,digest,Jsonb(document))).fetchone()
        if row is None:
            row = connection.execute('''SELECT capture_id FROM device_solar_capture
                WHERE tenant_id=%s AND plant_id=%s AND device_sha256=%s
                AND day_utc=%s AND document_sha256=%s''',
                (tenant_id,plant_id,device_hash,day,digest)).fetchone()
        return row[0]
