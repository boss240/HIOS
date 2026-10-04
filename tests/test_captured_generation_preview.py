from dataclasses import replace
from datetime import datetime,timedelta,timezone
from uuid import uuid4
import pytest
from app.captured_operational_weather import CapturedOperationalWeather,CaptureLineage
from app.operational_weather_composition import OperationalWeatherInterval
from app.captured_generation_preview import captured_generation_preview
from app.feature_assembly import PlantGeometry
from app.model_001 import Model001Config

ORIGIN=datetime(2026,6,21,8,tzinfo=timezone.utc)
GEOMETRY=PlantGeometry(50.54,30.62,30,180)
CONFIG=Model001Config('test',30,10,.85,-.004)
def inputs(start=ORIGIN+timedelta(hours=1),ghi=700):
    row=OperationalWeatherInterval(start,start+timedelta(hours=1),ghi,600,100,20,25,2,
        (('temperature_c','google_weather'),('irradiance_global_wm2','solcast')))
    sources=tuple(CaptureLineage(uuid4(),p,'v1','a'*64,ORIGIN-timedelta(minutes=1),None)
        for p in ('google_weather','solcast'))
    return CapturedOperationalWeather(ORIGIN,(row,),sources)

def test_candidate_retains_lineage_without_inventing_issue_time():
    source=inputs()
    point=captured_generation_preview(source,geometry=GEOMETRY,config=CONFIG)[0]
    assert 0<point.predicted_power_kw<=10
    assert point.predicted_energy_kwh==point.predicted_power_kw
    assert {'uncalibrated_candidate','air_temperature_proxy','provider_issue_time_unknown'}<=set(point.quality_flags)
    evidence=point.provider_provenance['weather_capture_sources']
    assert {s['capture_id'] for s in evidence}=={str(s.capture_id) for s in source.sources}
    assert all(s['provider_issued_at_utc'] is None for s in evidence)

def test_night_is_zero_and_ac_capacity_clips_daytime():
    source=inputs(start=datetime(2026,6,22,0,tzinfo=timezone.utc))
    night=captured_generation_preview(source,geometry=GEOMETRY,config=CONFIG)[0]
    assert night.predicted_energy_kwh==0 and 'solar_night' in night.quality_flags
    day=captured_generation_preview(inputs(),geometry=GEOMETRY,config=replace(CONFIG,ac_capacity_kw=1))[0]
    assert day.predicted_power_kw==1 and 'ac_clipped' in day.quality_flags

def test_late_receipt_started_target_or_overlapping_hours_fail():
    source=inputs()
    late=replace(source.sources[0],captured_at_utc=ORIGIN+timedelta(seconds=1))
    with pytest.raises(ValueError):captured_generation_preview(replace(source,sources=(late,source.sources[1])),geometry=GEOMETRY,config=CONFIG)
    with pytest.raises(ValueError):captured_generation_preview(inputs(start=ORIGIN),geometry=GEOMETRY,config=CONFIG)
    with pytest.raises(ValueError):captured_generation_preview(replace(source,intervals=source.intervals*2),geometry=GEOMETRY,config=CONFIG)

@pytest.mark.parametrize('ghi',[True,-1,float('nan'),float('inf')])
def test_invalid_physical_weather_fails(ghi):
    with pytest.raises(ValueError):captured_generation_preview(inputs(ghi=ghi),geometry=GEOMETRY,config=CONFIG)
