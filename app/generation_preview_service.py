"""Owner-scoped candidate preview from explicit captures and real passport data."""
from datetime import datetime,timezone
from uuid import UUID
from app.plant_onboarding import get_onboarding
from app.feature_assembly import PlantGeometry
from app.model_001 import Model001Config
from app.captured_operational_weather import load_captured_operational_weather
from app.captured_generation_preview import captured_generation_preview


class PlantPreviewNotReady(ValueError):
    def __init__(self, fields):
        super().__init__('plant passport incomplete')
        self.fields=tuple(fields)


def preview_configuration(profile: dict, *, performance_ratio, temperature_coefficient):
    required=('latitude','longitude','capacityKw','capacityAcKw','tiltDeg','azimuthDeg','meterBoundary')
    missing=[field for field in required if profile.get(field) is None or profile.get(field)=='']
    if missing:raise PlantPreviewNotReady(missing)
    # Database numeric types may be Decimal. Preserve explicit zeroes and reject
    # booleans rather than treating them as numeric capacities or geometry.
    def number(field):
        value=profile[field]
        if isinstance(value,bool):raise ValueError('numeric passport field required')
        return float(value)
    geometry=PlantGeometry(number('latitude'),number('longitude'),number('tiltDeg'),number('azimuthDeg'))
    config=Model001Config('MODEL-001-capture-preview-v1',number('capacityKw'),number('capacityAcKw'),
        performance_ratio,temperature_coefficient)
    if not isinstance(profile['meterBoundary'],str) or not profile['meterBoundary'].strip():
        raise ValueError('meter boundary required')
    return geometry,config


def preview_owned_captures(database_url: str, subject: str, *, tenant_id: str,plant_id: str,body: dict):
    profile=get_onboarding(database_url=database_url,subject=subject,tenant_id=tenant_id,plant_id=plant_id)
    if set(body)!={'captureIds','forecastOriginUtc','performanceRatio','temperatureCoefficientPerC'}:
        raise ValueError('explicit preview configuration and capture pair required')
    ids=body['captureIds']
    if not isinstance(ids,list) or len(ids)!=2 or any(not isinstance(id,str) for id in ids):
        raise ValueError('two capture UUIDs required')
    selected=tuple(UUID(id) for id in ids)
    origin=datetime.fromisoformat(body['forecastOriginUtc'])
    if origin.tzinfo is None or origin.utcoffset() is None or origin>datetime.now(timezone.utc):
        raise ValueError('aware nonfuture forecast origin required')
    geometry,config=preview_configuration(profile,performance_ratio=body['performanceRatio'],
        temperature_coefficient=body['temperatureCoefficientPerC'])
    inputs=load_captured_operational_weather(database_url,subject,tenant_id=tenant_id,plant_id=plant_id,
        capture_ids=selected,forecast_origin=origin)
    points=captured_generation_preview(inputs,geometry=geometry,config=config)
    return {'mode':'uncalibrated_candidate','persistence':'not_written','accuracy':'not_evaluated',
        'modelVersion':config.model_version,'forecastOriginUtc':inputs.forecast_origin_utc.isoformat(),
        'configuration':{'performanceRatio':config.performance_ratio,
            'temperatureCoefficientPerC':config.temperature_coefficient_per_c,'groundAlbedo':geometry.ground_albedo,
            'meterBoundary':profile['meterBoundary']},
        'points':[{'intervalStartUtc':p.interval_start_utc.isoformat(),'intervalEndUtc':p.interval_end_utc.isoformat(),
            'predictedPowerKw':p.predicted_power_kw,'predictedEnergyKwh':p.predicted_energy_kwh,
            'qualityFlags':list(p.quality_flags),'providerProvenance':p.provider_provenance} for p in points]}
