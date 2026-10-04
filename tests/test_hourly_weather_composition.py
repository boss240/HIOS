from datetime import datetime,timedelta,timezone
import pytest
from app.weather_provider_response import ProviderWeatherInterval
from app.operational_weather_composition import compose_hourly_operational_weather,OperationalWeatherCompositionError

START=datetime(2026,10,5,tzinfo=timezone.utc)
def google(start=START):
    return ProviderWeatherInterval('google_weather',start,start+timedelta(hours=1),
        {'temperature_c':12,'cloud_cover_pct':30,'wind_speed_ms':2})
def solar(offset,minutes=30,value=100,**kwargs):
    start=START+timedelta(minutes=offset)
    return ProviderWeatherInterval('solcast',start,start+timedelta(minutes=minutes),
        {'irradiance_global_wm2':value,'irradiance_direct_wm2':value,'irradiance_diffuse_wm2':value},**kwargs)
def compose(rows, g=None):
    return compose_hourly_operational_weather(google=(g or google(),),solcast=tuple(rows))

def test_two_half_hours_average_radiation_and_keep_google_role():
    result=compose([solar(0,value=100),solar(30,value=300),solar(60,value=999)])[0]
    assert result.irradiance_global_wm2 == 200
    assert result.temperature_c == 12
    assert dict(result.field_providers)['irradiance_global_wm2'] == 'solcast'
    assert dict(result.field_providers)['cloud_cover_pct'] == 'google_weather'
    assert result.interval_end_utc-result.valid_at_utc == timedelta(hours=1)

def test_duration_weighting_conserves_irradiation():
    assert compose([solar(0,15,100),solar(15,45,300)])[0].irradiance_global_wm2 == 250
    assert compose([solar(0,60,0)])[0].irradiance_global_wm2 == 0

@pytest.mark.parametrize('rows',[[solar(0)], [solar(0),solar(45,15)],
    [solar(-15,30),solar(15,45)], [solar(0,45),solar(30,30)],
    [solar(30),solar(0)], [solar(0),solar(0)]])
def test_gaps_clipping_overlap_and_disorder_fail(rows):
    with pytest.raises(OperationalWeatherCompositionError):compose(rows)

@pytest.mark.parametrize('value',[True,-1,float('nan'),float('inf'),'100'])
def test_invalid_radiation_fails(value):
    with pytest.raises(OperationalWeatherCompositionError):compose([solar(0,60,value)])

def test_instant_values_cannot_substitute_missing_interval_means():
    row=solar(0,60,instant_values={'irradiance_global_wm2':999},instant_at_utc=START)
    assert compose([row])[0].irradiance_global_wm2 == 100
    bad=ProviderWeatherInterval('solcast',START,START+timedelta(hours=1),{},row.values,START)
    with pytest.raises(OperationalWeatherCompositionError):compose([bad])

def test_google_hour_alignment_and_aware_timestamps_required():
    with pytest.raises(OperationalWeatherCompositionError):compose([solar(0,60)],google(START+timedelta(minutes=1)))
    with pytest.raises(OperationalWeatherCompositionError):compose([solar(0,60)],google(START.replace(tzinfo=None)))
