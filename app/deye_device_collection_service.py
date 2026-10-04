"""Owned, locked device PV collection using a verified read-only cloud binding."""
from datetime import datetime,timezone
from hashlib import sha256
from uuid import UUID
import psycopg
from app.deye_device_collection import collect_device_days
from app.deye_solar_archive import archive_window
from app.deye_solar_capture_store import store_device_solar_capture
from app.deye_station_reference import station_id_from_reference


def collect_bound_device(database_url,subject,*,tenant_id,plant_id,binding_id,
                         device_serial,start_day,end_day,client):
    archive_window(start_day,end_day)
    if end_day>=datetime.now(timezone.utc).date():
        raise ValueError('completed UTC days required')
    if not isinstance(binding_id,UUID):raise ValueError('explicit binding UUID required')
    if (not isinstance(device_serial,str) or not device_serial.strip()
            or device_serial!=device_serial.strip() or len(device_serial)>128):
        raise ValueError('explicit device required')
    device_hash=sha256(device_serial.encode()).hexdigest()
    with psycopg.connect(database_url,connect_timeout=5) as connection:
        binding=connection.execute('''SELECT b.external_plant_id FROM inverter_cloud_binding b
            JOIN plant p ON p.public_id=b.plant_id AND p.tenant_id=b.tenant_id
            JOIN membership m ON m.tenant_id=p.tenant_id
            WHERE b.binding_id=%s AND b.tenant_id=%s AND b.plant_id=%s
            AND b.provider='deye_cloud' AND b.discovery_status='verified' AND b.read_only
            AND m.subject=%s AND m.active FOR SHARE OF b,p,m''',
            (binding_id,tenant_id,plant_id,subject)).fetchone()
        if binding is None:raise PermissionError('verified owned binding required')
        station=int(station_id_from_reference(binding[0]))
        key=int.from_bytes(sha256(f'{tenant_id}:{plant_id}:{device_hash}'.encode()).digest()[:8],
                           'big',signed=True)
        if not connection.execute('SELECT pg_try_advisory_xact_lock(%s)',(key,)).fetchone()[0]:
            return ({'status':'already_running'},)
        token=None;verified=False
        class BoundClient:
            def obtain_token(self):
                nonlocal token,verified
                token=client.obtain_token()
                body=client.station_devices(token,(station,),size=100)
                rows=body.get('deviceListItems')
                if (not isinstance(rows,list) or len(rows)>=100 or
                    sum(isinstance(r,dict) and r.get('deviceSn')==device_serial for r in rows)!=1):
                    raise PermissionError('device must uniquely belong to bound station')
                verified=True
                return token
            def device_solar_history_for_day(self,request_token,serial,*,closed_day_utc):
                if not verified or serial!=device_serial:raise PermissionError('device scope denied')
                return client.device_solar_history_for_day(request_token,serial,closed_day_utc=closed_day_utc)
        def existing(day):
            return connection.execute('''SELECT 1 FROM device_solar_capture
                WHERE tenant_id=%s AND plant_id=%s AND device_sha256=%s AND day_utc=%s LIMIT 1''',
                (tenant_id,plant_id,device_hash,day)).fetchone() is not None
        def persist(day,body):
            store_device_solar_capture(database_url,subject,tenant_id=tenant_id,plant_id=plant_id,
                device_serial=device_serial,day=day,retrieved_at=datetime.now(timezone.utc),body=body)
        return collect_device_days(BoundClient(),device_serial=device_serial,start_day=start_day,
            end_day=end_day,existing_capture=existing,persist_capture=persist)
