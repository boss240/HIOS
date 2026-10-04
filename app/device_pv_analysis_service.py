"""Read explicit weather and device PV captures from the same owned plant."""
from datetime import datetime,timezone
from uuid import UUID
import psycopg
from app.captured_operational_weather import CaptureEvidence,compose_capture_evidence
from app.device_pv_weather_alignment import align_device_pv_weather


def analyze_owned_device_pv(database_url, subject, *, tenant_id, plant_id, body):
    if not isinstance(body,dict) or set(body)!={'weatherCaptureIds','solarCaptureId','forecastOriginUtc'}:
        raise ValueError('explicit source captures and forecast origin required')
    ids=body['weatherCaptureIds']
    if not isinstance(ids,list) or len(ids)!=2 or any(not isinstance(v,str) for v in ids):
        raise ValueError('two weather capture UUIDs required')
    weather_ids=tuple(UUID(v) for v in ids)
    if len(set(weather_ids))!=2 or not isinstance(body['solarCaptureId'],str):
        raise ValueError('distinct selected captures required')
    solar_id=UUID(body['solarCaptureId'])
    origin=datetime.fromisoformat(body['forecastOriginUtc'])
    now=datetime.now(timezone.utc)
    if origin.tzinfo is None or origin.utcoffset() is None or origin>now:
        raise ValueError('aware nonfuture origin required')
    with psycopg.connect(database_url,connect_timeout=5) as connection:
        allowed=connection.execute('''SELECT 1 FROM plant p JOIN membership m
            ON m.tenant_id=p.tenant_id WHERE p.tenant_id=%s AND p.public_id=%s
            AND m.subject=%s AND m.active FOR SHARE OF p,m''',
            (tenant_id,plant_id,subject)).fetchone()
        if allowed is None:raise PermissionError('owned active plant required')
        weather=connection.execute('''SELECT capture_id,document_sha256,document
            FROM provider_forecast_capture WHERE tenant_id=%s AND plant_id=%s
            AND capture_id=ANY(%s)''',(tenant_id,plant_id,list(weather_ids))).fetchall()
        solar=connection.execute('''SELECT document_sha256,retrieved_at_utc,document
            FROM device_solar_capture WHERE tenant_id=%s AND plant_id=%s
            AND capture_id=%s''',(tenant_id,plant_id,solar_id)).fetchone()
        if len(weather)!=2 or solar is None:
            raise PermissionError('all selected captures must belong to the same plant')
    inputs=compose_capture_evidence(tuple(CaptureEvidence(*row) for row in weather),forecast_origin=origin)
    return align_device_pv_weather(inputs,solar[2],solar_capture_id=solar_id,
        solar_sha256=solar[0],solar_retrieved_at=solar[1],analysis_as_of=now)
