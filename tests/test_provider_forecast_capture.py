from dataclasses import replace
from datetime import datetime, timedelta, timezone
import pytest
from app.provider_forecast_capture import capture_document
from app.weather_provider_response import ProviderWeatherInterval

CAPTURED = datetime(2026,10,4,10,tzinfo=timezone.utc)
ROW = ProviderWeatherInterval('open_meteo', CAPTURED+timedelta(hours=1),
    CAPTURED+timedelta(hours=2), {'irradiance_global_wm2':500},
    {'temperature_c':20}, CAPTURED+timedelta(hours=2))

def document(rows=(ROW,), **changes):
    options = dict(provider='open_meteo',mapping_version='open-meteo-v2',
        captured_at=CAPTURED,intervals=rows)
    options.update(changes)
    return capture_document(**options)

def test_retains_receipt_without_inventing_issue_or_missing_fields():
    result = document()
    assert result['provider_issued_at'] is None
    assert result['intervals'][0]['values'] == {'irradiance_global_wm2':500.0}
    assert result['intervals'][0]['instant_values'] == {'temperature_c':20.0}
    assert result['intervals'][0]['instant_at'] == ROW.interval_end_utc.isoformat()
    assert 'cloud_cover_pct' not in result['intervals'][0]['values']

@pytest.mark.parametrize('row', [
    replace(ROW,valid_at_utc=CAPTURED),
    replace(ROW,provider='solcast'),
    replace(ROW,values={'irradiance_global_wm2':float('nan')}),
    replace(ROW,values={'token':123}),
    replace(ROW,instant_at_utc=CAPTURED),
])
def test_rejects_late_mixed_unmapped_or_invalid_evidence(row):
    with pytest.raises(ValueError):
        document((row,))

def test_duplicate_intervals_cannot_bias_comparison():
    with pytest.raises(ValueError):
        document((ROW,ROW))

def test_provider_issue_time_must_not_follow_receipt():
    with pytest.raises(ValueError):
        document(provider_issued_at=CAPTURED+timedelta(seconds=1))

def test_mapping_changes_do_not_mutate_frozen_document():
    values = {'irradiance_global_wm2':500}
    result = document((replace(ROW,values=values),))
    values['irradiance_global_wm2'] = 1
    assert result['intervals'][0]['values']['irradiance_global_wm2'] == 500
