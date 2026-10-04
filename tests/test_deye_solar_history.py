from datetime import date
import pytest
from app.deye_solar_history import solar_power_samples, solar_hourly_preview


def row(t, value='1000', unit='W'):
    return {'time': str(t), 'itemList': [
        {'key': 'TotalSolarPower', 'value': value, 'unit': unit},
        {'key': 'PVDailyPowerGenerationActive', 'value': '99', 'unit': 'kWh'}]}


def test_explicit_device_power_integrates_without_summing_daily_counter():
    base = 1577836800
    body = {'deviceSn': 'private', 'dataList': [row(base+t) for t in range(0, 3601, 300)]}
    result = solar_hourly_preview(body, day=date(2020, 1, 1))
    assert result[0]['derivedEnergyKwh'] == pytest.approx(1)
    assert result[0]['complete']
    assert result[1]['derivedEnergyKwh'] is None
    assert 'private' not in str(result)


@pytest.mark.parametrize('value', [None, '', 'NaN', 'Infinity', '-1', True])
def test_invalid_sample_breaks_interpolation(value):
    base = 1577836800
    body = {'dataList': [row(base), row(base+300, value), row(base+600)]}
    result = solar_hourly_preview(body, day=date(2020, 1, 1))
    assert result[0]['coveredSeconds'] == 0
    assert result[0]['derivedEnergyKwh'] is None


@pytest.mark.parametrize('unit', [None, '', 'kW', 'kWh'])
def test_unit_ambiguity_rejected(unit):
    with pytest.raises(ValueError):
        solar_power_samples({'dataList': [row(1577836800, unit=unit)]})


@pytest.mark.parametrize('stamp', ['2020-01-01T00:00:00', '1577836800000', True, None])
def test_timestamp_ambiguity_rejected(stamp):
    sample = row(1577836800)
    sample['time'] = stamp
    with pytest.raises(ValueError):
        solar_power_samples({'dataList': [sample]})


def test_duplicate_measurement_and_unordered_times_rejected():
    sample = row(1577836800)
    sample['itemList'].append(sample['itemList'][0])
    with pytest.raises(ValueError): solar_power_samples({'dataList': [sample]})
    with pytest.raises(ValueError):
        solar_power_samples({'dataList': [row(1577836801), row(1577836800)]})


def test_wrong_device_history_is_rejected_before_database_access():
    from datetime import datetime, timezone
    from app.deye_solar_capture_store import store_device_solar_capture
    with pytest.raises(ValueError, match='match selected device'):
        store_device_solar_capture('must-not-connect', 'alice', tenant_id='a', plant_id='p',
            device_serial='selected', day=date(2020,1,1),
            retrieved_at=datetime(2020,1,2,tzinfo=timezone.utc),
            body={'deviceSn':'different','dataList':[row(1577836800)]})
