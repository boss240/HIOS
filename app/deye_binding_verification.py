"""Server-only read-only proof of access for one explicitly owned Deye binding."""
from uuid import UUID
import psycopg
from app.deye_station_reference import station_id_from_reference
from app.deye_station_discovery import station_candidates


def verify_deye_binding(database_url,subject,*,tenant_id,plant_id,binding_id,
                        credential_reference,client):
    """Verify exact station access with server-resolved credentials, no retries.

    The caller resolves credential_reference through an approved server secret
    store. No API endpoint may accept credential values or assign verified status.
    A station absent from the bounded account page remains unverified.
    """
    if not isinstance(binding_id,UUID):raise ValueError('binding UUID required')
    if not isinstance(credential_reference,str) or not credential_reference.strip():
        raise ValueError('server credential reference required')
    with psycopg.connect(database_url,connect_timeout=5) as connection:
        row=connection.execute('''SELECT b.external_plant_id,b.credential_reference
            FROM inverter_cloud_binding b
            JOIN plant p ON p.public_id=b.plant_id AND p.tenant_id=b.tenant_id
            JOIN membership m ON m.tenant_id=p.tenant_id
            WHERE b.binding_id=%s AND b.tenant_id=%s AND b.plant_id=%s
            AND b.provider='deye_cloud' AND b.read_only AND m.subject=%s AND m.active
            FOR UPDATE OF b FOR SHARE OF p,m''',(binding_id,tenant_id,plant_id,subject)).fetchone()
        if row is None or row[1]!=credential_reference:
            raise PermissionError('owned binding and resolved credential reference required')
        station=int(station_id_from_reference(row[0]))
        token=client.obtain_token()
        candidates=station_candidates(client.list_stations(token,page=1,size=100))
        if not any(c.station_id==station for c in candidates):
            raise PermissionError('selected station was not confirmed in account')
        response=client.station_devices(token,(station,),size=100)
        devices=response.get('deviceListItems')
        if not isinstance(devices,list) or not devices or len(devices)>=100:
            raise ValueError('bounded device evidence required')
        serials=[d.get('deviceSn') if isinstance(d,dict) else None for d in devices]
        if any(not isinstance(s,str) or not s.strip() for s in serials) or len(set(serials))!=len(serials):
            raise ValueError('unambiguous device evidence required')
        connection.execute("UPDATE inverter_cloud_binding SET discovery_status='verified' WHERE binding_id=%s",(binding_id,))
        return {'status':'verified','readOnly':True,'deviceCount':len(devices)}
