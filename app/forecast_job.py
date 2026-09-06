"""Controlled in-process orchestration for the deterministic Sprint 2 baseline."""
from dataclasses import asdict, dataclass
import hashlib
import json

from app.feature_assembly import FEATURE_SCHEMA_VERSION, PlantGeometry, build_model_001_features
from app.forecast_store import ForecastPoint, ForecastRun, create_or_get_run, publish_points
from app.model_001 import Model001Config, predict
from app.model_registry import resolve_approved_candidate
from app.weather_normalization import NormalizedWeather


@dataclass(frozen=True)
class ForecastWeatherInput:
    source_reference: str
    weather: NormalizedWeather


@dataclass(frozen=True)
class ForecastJobResult:
    run_id: object
    published_points: int
    input_hash: str


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def configuration_hash(config: Model001Config, geometry: PlantGeometry) -> str:
    """Hash the complete deterministic configuration required for MODEL-001."""
    return _hash({"model": asdict(config), "geometry": asdict(geometry),
                  "feature_schema_version": FEATURE_SCHEMA_VERSION})


def input_hash(inputs: tuple[ForecastWeatherInput, ...]) -> str:
    """Hash normalized weather and immutable source references in interval order."""
    if not inputs:
        raise ValueError("at least one weather interval is required")
    records = []
    for item in sorted(inputs, key=lambda value: value.weather.valid_at_utc):
        if not item.source_reference.strip():
            raise ValueError("weather source_reference must be non-empty")
        weather = asdict(item.weather)
        records.append({key: value.isoformat() if hasattr(value, "isoformat") else value
                        for key, value in weather.items()} | {"source_reference": item.source_reference})
    if len({record["valid_at_utc"] for record in records}) != len(records):
        raise ValueError("weather intervals must have unique valid_at_utc values")
    return _hash(records)


def execute_model_001(*, database_url: str, subject: str, run: ForecastRun,
                      config: Model001Config, geometry: PlantGeometry,
                      weather_inputs: tuple[ForecastWeatherInput, ...]) -> ForecastJobResult:
    """Validate lineage, build every point, then persist the run and points.

    This has no scheduler, network client or automatic promotion. Any invalid
    weather/configuration blocks before a run is written; reruns are idempotent.
    """
    candidate = resolve_approved_candidate(database_url, subject, run.tenant_id, run.plant_id, "MODEL-001")
    expected_config_hash = configuration_hash(config, geometry)
    expected_input_hash = input_hash(weather_inputs)
    if (run.model_id, run.model_version, run.feature_version, run.configuration_hash, run.input_hash, run.code_commit) != (
        candidate.model_id, candidate.model_version, candidate.feature_schema_version,
        candidate.configuration_hash, expected_input_hash, candidate.code_commit,
    ):
        raise ValueError("forecast run lineage does not match the approved model and supplied inputs")
    if config.model_version != candidate.model_version or expected_config_hash != candidate.configuration_hash:
        raise ValueError("MODEL-001 configuration does not match the approved candidate")
    points = []
    for item in sorted(weather_inputs, key=lambda value: value.weather.valid_at_utc):
        features = build_model_001_features(weather=item.weather, geometry=geometry,
                                            forecast_origin_utc=run.forecast_origin_utc)
        output = predict(config, features.model_input)
        hours = (item.weather.interval_end_utc - item.weather.valid_at_utc).total_seconds() / 3600
        points.append(ForecastPoint(
            interval_start_utc=item.weather.valid_at_utc,
            interval_end_utc=item.weather.interval_end_utc,
            predicted_power_kw=output.predicted_power_kw,
            predicted_energy_kwh=output.predicted_power_kw * hours,
            quality_flags=output.quality_flags,
            provider_provenance={"weather_source_reference": item.source_reference,
                                 "weather_provider": item.weather.provider},
        ))
    run_id = create_or_get_run(database_url, subject, run)
    published = publish_points(database_url, subject, run.tenant_id, run_id, tuple(points))
    return ForecastJobResult(run_id, published, expected_input_hash)
