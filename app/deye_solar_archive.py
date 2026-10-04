"""Bounded tenant-owned device PV evidence; no external requests or writes."""
from datetime import date, datetime
import psycopg


def archive_window(start_day, end_day):
    if any(isinstance(v, datetime) or not isinstance(v, date) for v in (start_day,end_day)):
        raise ValueError('calendar dates required')
    if not 0 <= (end_day-start_day).days <= 30:
        raise ValueError('ordered window of at most 31 days required')
    return start_day,end_day


def list_device_solar_archive(database_url, subject, *, tenant_id, plant_id,
                              start_day, end_day):
    start,end=archive_window(start_day,end_day)
    with psycopg.connect(database_url,connect_timeout=5) as connection:
        allowed=connection.execute('''SELECT 1 FROM plant p JOIN membership m
            ON m.tenant_id=p.tenant_id WHERE p.tenant_id=%s AND p.public_id=%s
            AND m.subject=%s AND m.active FOR SHARE OF p,m''',
            (tenant_id,plant_id,subject)).fetchone()
        if allowed is None:
            raise PermissionError('active membership and owned plant required')
        rows=connection.execute('''SELECT capture_id,day_utc,retrieved_at_utc,
            document_sha256,document FROM (
                SELECT DISTINCT ON(day_utc,device_sha256) * FROM device_solar_capture
                WHERE tenant_id=%s AND plant_id=%s AND day_utc BETWEEN %s AND %s
                ORDER BY day_utc,device_sha256,retrieved_at_utc DESC,capture_id DESC
            ) selected ORDER BY day_utc,capture_id LIMIT 125''',
            (tenant_id,plant_id,start,end)).fetchall()
    if len(rows)>124:
        raise ValueError('archive window contains too many device captures')
    return tuple({'captureId':str(r[0]),'dayUtc':r[1].isoformat(),
                  'retrievedAtUtc':r[2].isoformat(),'documentSha256':r[3],
                  'scope':'device_only','field':'TotalSolarPower','powerUnit':'W',
                  'mappingVersion':r[4]['mappingVersion'],
                  'sampleCount':len(r[4]['samples']),
                  'hours':r[4]['hours']} for r in rows)
