from decimal import Decimal
import pytest
from app.generation_preview_service import preview_configuration,PlantPreviewNotReady

PROFILE={'latitude':50.54,'longitude':30.62,'capacityKw':Decimal('30'),
    'capacityAcKw':10,'tiltDeg':30,'azimuthDeg':180,'meterBoundary':'AC inverter output'}
def config(profile):return preview_configuration(profile,performance_ratio=.85,temperature_coefficient=-.004)

def test_explicit_numeric_passport_config_preserves_zero_angles():
    geometry,model=config(PROFILE|{'tiltDeg':0,'azimuthDeg':0})
    assert geometry.tilt_degrees==geometry.surface_azimuth_degrees==0
    assert model.dc_capacity_kw==30 and model.ac_capacity_kw==10

def test_missing_real_geometry_has_no_defaults():
    with pytest.raises(PlantPreviewNotReady) as exc:config({'latitude':50,'longitude':30})
    assert exc.value.fields==('capacityKw','capacityAcKw','tiltDeg','azimuthDeg','meterBoundary')

@pytest.mark.parametrize('change',[{'capacityKw':True},{'capacityAcKw':0},{'tiltDeg':100},
    {'azimuthDeg':float('nan')},{'meterBoundary':'  '}])
def test_invalid_passport_blocks_preview(change):
    with pytest.raises(ValueError):config(PROFILE|change)
