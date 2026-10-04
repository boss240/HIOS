"""Exact hourly weather/device-PV pairing, not generation accuracy scoring."""
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from uuid import UUID
from app.deye_power_integration import integrate_power_day


def _utc(value):
    if not isinstance(value,datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('aware timestamps required')
    return value.astimezone(timezone.utc)


def align_device_pv_weather(weather, solar_document, *, solar_capture_id, solar_sha256,
                            solar_retrieved_at, analysis_as_of):
    """Retain complete closed UTC hours and separate units with source lineage.

    Weather must come from compose_capture_evidence's validated selected captures.
    Caller must establish common plant/tenant ownership for the selected inputs.
    Solar energy is a derived device estimate; AC forecast error cannot be scored
    against it without an independently established compatible measurement scope.
    """
    as_of=_utc(analysis_as_of);receipt=_utc(solar_retrieved_at)
    if not isinstance(solar_capture_id,UUID):raise ValueError('selected solar capture UUID required')
    origin=_utc(weather.forecast_origin_utc)
    if receipt>as_of or origin>as_of:
        raise ValueError('evidence must be known at analysis time')
    digest=hashlib.sha256(json.dumps(solar_document,sort_keys=True,separators=(',',':'),
                                  allow_nan=False).encode()).hexdigest()
    if digest!=solar_sha256:raise ValueError('solar capture checksum mismatch')
    if (solar_document.get('scope')!='device_only' or solar_document.get('unit')!='W'
            or solar_document.get('field')!='TotalSolarPower'
            or solar_document.get('mappingVersion')!='deye-device-solar-v1'):
        raise ValueError('canonical device solar capture required')
    day=date.fromisoformat(solar_document['dayUtc'])
    if day>=receipt.date():raise ValueError('solar day must precede receipt')
    replay=integrate_power_day(solar_document['samples'],day=day,power_unit='W')
    if list(replay)!=solar_document['hours']:
        raise ValueError('solar hours do not reproduce from stored samples')
    actual={datetime.fromisoformat(h['hourUtc']):h for h in replay}
    exclusions={'not_closed':0,'actual_missing':0,'actual_partial':0}
    pairs=[];seen=set()
    for row in weather.intervals:
        start,end=_utc(row.valid_at_utc),_utc(row.interval_end_utc)
        if start<=origin or end-start!=timedelta(hours=1) or start.minute or start.second or start.microsecond:
            raise ValueError('weather targets must be complete future UTC hours')
        if start in seen:raise ValueError('duplicate weather hour')
        seen.add(start)
        if end>as_of:
            exclusions['not_closed']+=1;continue
        hour=actual.get(start)
        if hour is None or hour['derivedEnergyKwh'] is None:
            exclusions['actual_missing']+=1;continue
        if not hour['complete'] or hour['coveredSeconds']!=3600:
            exclusions['actual_partial']+=1;continue
        pairs.append({'hourUtc':start.isoformat(),'intervalEndUtc':end.isoformat(),
            'forecastGhiWm2':row.irradiance_global_wm2,
            'forecastDniWm2':row.irradiance_direct_wm2,
            'forecastDhiWm2':row.irradiance_diffuse_wm2,
            'forecastCloudCoverPct':row.cloud_cover_pct,
            'forecastTemperatureC':row.temperature_c,
            'derivedDevicePvEnergyKwh':hour['derivedEnergyKwh']})
    return {'mode':'weather_device_pv_alignment','generationAccuracy':'not_evaluated',
        'forecastOriginUtc':origin.isoformat(),'analysisAsOfUtc':as_of.isoformat(),
        'solarCaptureId':str(solar_capture_id),
        'solarDocumentSha256':digest,'solarRetrievedAtUtc':receipt.isoformat(),
        'scope':'device_only','pairs':pairs,'excludedCounts':exclusions,
        'weatherSources':[{'captureId':str(s.capture_id),'provider':s.provider,
            'documentSha256':s.document_sha256,'capturedAtUtc':s.captured_at_utc.isoformat(),
            'providerIssuedAtUtc':None if s.provider_issued_at_utc is None else s.provider_issued_at_utc.isoformat()}
            for s in weather.sources]}
