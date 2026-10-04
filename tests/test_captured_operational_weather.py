from dataclasses import replace
from datetime import datetime,timedelta,timezone
import hashlib,json
from uuid import uuid4
import pytest
from app.captured_operational_weather import CaptureEvidence,compose_capture_evidence
from app.provider_forecast_capture import capture_document
from app.weather_provider_response import ProviderWeatherInterval

NOW=datetime(2026,10,4,10,tzinfo=timezone.utc)
def sources():
    results=[]
    for provider,values in [('google_weather',{'temperature_c':12,'cloud_cover_pct':30,'wind_speed_ms':2}),
        ('solcast',{'irradiance_global_wm2':100,'irradiance_direct_wm2':80,'irradiance_diffuse_wm2':20})]:
        step=60 if provider=='google_weather' else 30
        rows=tuple(ProviderWeatherInterval(provider,NOW+timedelta(minutes=offset),NOW+timedelta(minutes=offset+step),values)
            for offset in range(60,180,step))
        doc=capture_document(provider=provider,mapping_version='v1',captured_at=NOW,intervals=rows)
        digest=hashlib.sha256(json.dumps(doc,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
        results.append(CaptureEvidence(uuid4(),digest,doc))
    return tuple(results)

def test_selected_capture_lineage_retains_unknown_issue_time_and_receipt():
    evidence=sources();result=compose_capture_evidence(evidence,forecast_origin=NOW+timedelta(minutes=1))
    assert len(result.intervals)==2
    assert {s.capture_id for s in result.sources} == {s.capture_id for s in evidence}
    assert all(s.provider_issued_at_utc is None and s.captured_at_utc==NOW for s in result.sources)
    assert result.forecast_origin_utc==NOW+timedelta(minutes=1)

def test_later_replay_origin_excludes_started_hour():
    result=compose_capture_evidence(sources(),forecast_origin=NOW+timedelta(hours=1))
    assert len(result.intervals)==1
    assert result.intervals[0].valid_at_utc==NOW+timedelta(hours=2)

def test_capture_after_origin_and_checksum_tampering_fail():
    evidence=sources()
    with pytest.raises(ValueError,match='after'):compose_capture_evidence(evidence,forecast_origin=NOW-timedelta(seconds=1))
    evidence[0].document['intervals'][0]['values']['temperature_c']=50
    with pytest.raises(ValueError,match='checksum'):compose_capture_evidence(evidence,forecast_origin=NOW)

def test_duplicate_capture_or_provider_cannot_form_pair():
    evidence=sources()
    with pytest.raises(ValueError):compose_capture_evidence((evidence[0],evidence[0]),forecast_origin=NOW)
    with pytest.raises(ValueError):compose_capture_evidence((evidence[0],replace(evidence[0],capture_id=uuid4())),forecast_origin=NOW)
