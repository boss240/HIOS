"""Idempotent owner-confirmed pending binding using server credentials only."""
from uuid import uuid4
import psycopg
from app.deye_station_reference import station_id_from_reference

SERVER_CREDENTIAL_REFERENCE='server-env://deye-dashboard-v1'


def prepare_dashboard_binding(database_url,subject,*,tenant_id,plant_id,station_reference):
    station=station_id_from_reference(station_reference)
    with psycopg.connect(database_url,connect_timeout=5) as connection:
        owned=connection.execute('''SELECT 1 FROM plant p JOIN membership m ON m.tenant_id=p.tenant_id
            WHERE p.tenant_id=%s AND p.public_id=%s AND m.subject=%s AND m.active
            FOR SHARE OF p,m''',(tenant_id,plant_id,subject)).fetchone()
        if owned is None:raise PermissionError('owned plant required')
        row=connection.execute('''INSERT INTO inverter_cloud_binding(binding_id,tenant_id,plant_id,
            provider,external_plant_id,credential_reference,consent_record_reference,mapping_version)
            VALUES (%s,%s,%s,'deye_cloud',%s,%s,%s,'deye-device-solar-v1')
            ON CONFLICT(tenant_id,plant_id,provider,external_plant_id) DO NOTHING RETURNING binding_id''',
            (uuid4(),tenant_id,plant_id,station,SERVER_CREDENTIAL_REFERENCE,
             'dashboard-read-only-confirmation:'+str(uuid4()))).fetchone()
        if row is None:
            row=connection.execute('''SELECT binding_id FROM inverter_cloud_binding
                WHERE tenant_id=%s AND plant_id=%s AND provider='deye_cloud'
                AND external_plant_id=%s AND credential_reference=%s AND read_only''',
                (tenant_id,plant_id,station,SERVER_CREDENTIAL_REFERENCE)).fetchone()
        if row is None:raise PermissionError('existing binding uses another credential source')
        return row[0]
