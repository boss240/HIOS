from datetime import date
import pytest
from app.deye_power_integration import integrate_power_day

DAY = date(2024, 9, 1)
START = 1725148800
def sample(seconds, power):
    return {'timeStamp':START+seconds, 'generationPower':power}
def run(rows, **kwargs):
    return integrate_power_day(rows, day=DAY, power_unit='W', **kwargs)

def test_constant_power_and_unit_equivalence():
    rows=[sample(t, 2000) for t in range(0,3601,300)]
    result=run(rows)
    assert result[0]['derivedEnergyKwh'] == pytest.approx(2)
    assert result[0]['complete']
    assert result[1]['derivedEnergyKwh'] is None
    kw=integrate_power_day([sample(t,2) for t in range(0,3601,300)],day=DAY,power_unit='kW')
    assert kw == result

def test_ramp_crossing_hour_is_split_by_interpolation():
    result=run([sample(3300,0), sample(3900,6000)])
    assert result[0]['derivedEnergyKwh'] == pytest.approx(.125)
    assert result[1]['derivedEnergyKwh'] == pytest.approx(.375)
    assert result[0]['coveredSeconds'] == result[1]['coveredSeconds'] == 300

def test_day_boundaries_are_clipped_and_never_extrapolated():
    result=run([sample(-300,1000),sample(300,1000),sample(86100,1000),sample(86700,1000)])
    assert result[0]['coveredSeconds'] == result[23]['coveredSeconds'] == 300
    assert all(not r['complete'] for r in result)

@pytest.mark.parametrize('invalid',[None,True,-1,float('nan'),float('inf'),'1000'])
def test_invalid_sample_breaks_both_adjacent_segments(invalid):
    result=run([sample(0,1000),sample(300,invalid),sample(600,1000),sample(900,1000)])
    assert result[0]['coveredSeconds'] == 300
    assert result[0]['derivedEnergyKwh'] == pytest.approx(1/12)

def test_gap_and_duplicate_are_not_silently_repaired():
    assert run([sample(0,1000),sample(601,1000)])[0]['coveredSeconds'] == 0
    with pytest.raises(ValueError):run([sample(0,1000),sample(0,1000)])
    with pytest.raises(ValueError):run([sample(300,1000),sample(0,1000)])

@pytest.mark.parametrize('unit',[None,'auto','MW','w'])
def test_unit_is_never_inferred(unit):
    with pytest.raises(ValueError):integrate_power_day([],day=DAY,power_unit=unit)

@pytest.mark.parametrize('stamp',[True,float('nan'),START+.5,'1725148800'])
def test_bad_timestamp_rejects_batch(stamp):
    with pytest.raises(ValueError):run([{'timeStamp':stamp,'generationPower':1000}])
