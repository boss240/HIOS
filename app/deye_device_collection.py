"""Bounded device PV collection orchestration for an authorised selected device.

The caller must authorise the tenant, plant and device before invoking this
helper and hold its collection lock until it returns. Persistence must use
store_device_solar_capture, keeping device PV separate from plant AC actuals.
"""
from datetime import date, datetime, timedelta, timezone
from app.deye_solar_archive import archive_window


def collect_device_days(client, *, device_serial, start_day, end_day,
                        existing_capture, persist_capture, now=None):
    """Skip saved days before authentication; stop at the first failed operation.

    No retries, no implicit device discovery, no native identifiers or exception
    messages in outcomes. Callbacks operate in the caller's validated scope.
    A partial saved day remains evidence, not an invented complete measurement.
    """
    start,end=archive_window(start_day,end_day)
    current=now or datetime.now(timezone.utc)
    if (not isinstance(current,datetime) or current.tzinfo is None
            or current.utcoffset() is None):
        raise ValueError('aware collection clock required')
    if end>=current.astimezone(timezone.utc).date():
        raise ValueError('only completed UTC days may be collected')
    if (not isinstance(device_serial,str) or not device_serial.strip()
            or device_serial!=device_serial.strip() or len(device_serial)>128):
        raise ValueError('explicit selected device required')
    outcomes=[];token=None
    for offset in range((end-start).days+1):
        day=start+timedelta(days=offset)
        try:
            if existing_capture(day):
                outcomes.append({'dayUtc':day.isoformat(),'status':'already_stored'})
                continue
            if token is None:
                token=client.obtain_token()
            body=client.device_solar_history_for_day(token,device_serial,closed_day_utc=day)
            persist_capture(day,body)
            outcomes.append({'dayUtc':day.isoformat(),'status':'stored'})
        except Exception as error:
            outcomes.append({'dayUtc':day.isoformat(),'status':'failed',
                             'errorClass':type(error).__name__})
            break
    return tuple(outcomes)
