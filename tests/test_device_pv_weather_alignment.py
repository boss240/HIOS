from datetime import date,datetime,timedelta,timezone
from dataclasses import replace
from uuid import uuid4
import json,hashlib
import pytest
from app.deye_power_integration import integrate_power_day
from app.captured_operational_weather import CapturedOperationalWeather,CaptureLineage
from app.operational_weather_composition import OperationalWeatherInterval
from app.device_pv_weather_alignment import align_device_pv_weather

ORIGIN=datetime(2026,6,21,8,tzinfo=timezone.utc)
RECEIPT=datetime(2026,6,22,tzinfo=timezone.utc)


def solar():
    start=int((ORIGIN+timedelta(hours=1)).timestamp())
    samples=[{'timeStamp':start+t,'generationPower':1000.0} for t in range(0,6601,300)]
    doc={'mappingVersion':'deye-device-solar-v1','dayUtc':'2026-06-21',
         'scope':'device_only','unit':'W','field':'TotalSolarPower','samples':samples,
         'hours':integrate_power_day(samples,day=date(2026,6,21),power_unit='W')}
    return json.loads(json.dumps(doc))


def weather(starts=None):
    starts=starts or [ORIGIN+timedelta(hours=h) for h in (1,2,3)]
    rows=tuple(OperationalWeatherInterval(s,s+timedelta(hours=1),500,400,100,20,25,2,()) for s in starts)
    sources=tuple(CaptureLineage(uuid4(),p,'v1','a'*64,ORIGIN,None) for p in ('google_weather','solcast'))
    return CapturedOperationalWeather(ORIGIN,rows,sources)


def align(doc=None, inputs=None, **changes):
    doc=solar() if doc is None else doc
    options={'solar_capture_id':uuid4(),'solar_sha256':hashlib.sha256(json.dumps(doc,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest(),
             'solar_retrieved_at':RECEIPT,'analysis_as_of':RECEIPT+timedelta(hours=1)}
    options.update(changes)
    return align_device_pv_weather(inputs or weather(),doc,**options)


def test_exact_hours_separate_units_and_retain_unknown_issue_time():
    result=align()
    assert len(result['pairs'])==1
    assert result['pairs'][0]['derivedDevicePvEnergyKwh']==pytest.approx(1)
    assert result['pairs'][0]['forecastGhiWm2']==500
    assert result['excludedCounts']=={'not_closed':0,'actual_missing':1,'actual_partial':1}
    assert result['generationAccuracy']=='not_evaluated'
    assert all(s['providerIssuedAtUtc'] is None for s in result['weatherSources'])


def test_future_targets_cannot_be_evaluation_pairs():
    result=align(inputs=weather([RECEIPT+timedelta(hours=2)]))
    assert result['pairs']==[] and result['excludedCounts']['not_closed']==1


def test_zero_generation_is_preserved_in_complete_hour():
    doc=solar()
    for sample in doc['samples']:sample['generationPower']=0
    doc['hours']=list(integrate_power_day(doc['samples'],day=date(2026,6,21),power_unit='W'))
    assert align(doc)['pairs'][0]['derivedDevicePvEnergyKwh']==0


def test_hash_or_replayed_hour_tampering_rejected():
    with pytest.raises(ValueError,match='checksum'):align(solar_sha256='0'*64)
    doc=solar();doc['hours'][9]['derivedEnergyKwh']=999
    with pytest.raises(ValueError,match='reproduce'):align(doc)


def test_late_actual_receipt_and_naive_clock_rejected():
    with pytest.raises(ValueError):align(solar_retrieved_at=RECEIPT+timedelta(days=1))
    with pytest.raises(ValueError):align(analysis_as_of=RECEIPT.replace(tzinfo=None))


def test_duplicate_and_non_hourly_weather_rejected():
    row=weather().intervals[0]
    with pytest.raises(ValueError):align(inputs=replace(weather(),intervals=(row,row)))
    with pytest.raises(ValueError):align(inputs=replace(weather(),intervals=(replace(row,interval_end_utc=row.valid_at_utc+timedelta(minutes=30)),)))
