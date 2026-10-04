"""Pure candidate generation estimates from selected immutable weather captures.

No defaults for plant geometry/model configuration, database writes, production
release or calibrated accuracy claims belong in this adapter.
"""
from app.captured_operational_weather import CapturedOperationalWeather
from app.feature_assembly import PlantGeometry, build_captured_model_001_features
from app.model_001 import Model001Config, predict
from app.forecast_store import ForecastPoint


def captured_generation_preview(inputs: CapturedOperationalWeather, *,
        geometry: PlantGeometry, config: Model001Config) -> tuple[ForecastPoint, ...]:
    if len(inputs.sources)!=2 or {s.provider for s in inputs.sources}!={'google_weather','solcast'}:
        raise ValueError('Google and Solcast lineage required')
    if any(s.captured_at_utc>inputs.forecast_origin_utc or
           s.provider_issued_at_utc is not None and s.provider_issued_at_utc>s.captured_at_utc
           for s in inputs.sources):
        raise ValueError('source not available at origin')
    receipt=max(s.captured_at_utc for s in inputs.sources)
    issued=max(s.provider_issued_at_utc for s in inputs.sources) if all(s.provider_issued_at_utc is not None for s in inputs.sources) else None
    lineage=[{'capture_id':str(s.capture_id),'provider':s.provider,'mapping_version':s.mapping_version,
        'document_sha256':s.document_sha256,'captured_at_utc':s.captured_at_utc.isoformat(),
        'provider_issued_at_utc':None if s.provider_issued_at_utc is None else s.provider_issued_at_utc.isoformat()}
        for s in sorted(inputs.sources,key=lambda s:s.provider)]
    points=[]
    previous_end=None
    for interval in inputs.intervals:
        if previous_end is not None and interval.valid_at_utc<previous_end:
            raise ValueError('ordered non-overlapping forecast intervals required')
        previous_end=interval.interval_end_utc
        features=build_captured_model_001_features(weather=interval,geometry=geometry,
            forecast_origin_utc=inputs.forecast_origin_utc,captured_at_utc=receipt,provider_issued_at_utc=issued)
        output=predict(config,features.model_input)
        flags=output.quality_flags+('uncalibrated_candidate','air_temperature_proxy')
        if issued is None:flags+=('provider_issue_time_unknown',)
        hours=(interval.interval_end_utc-interval.valid_at_utc).total_seconds()/3600
        points.append(ForecastPoint(interval.valid_at_utc,interval.interval_end_utc,output.predicted_power_kw,
            output.predicted_power_kw*hours,flags,{'weather_capture_sources':lineage,
                'field_providers':dict(interval.field_providers),'forecast_origin_utc':inputs.forecast_origin_utc.isoformat()}))
    if not points:raise ValueError('future weather intervals required')
    return tuple(points)
