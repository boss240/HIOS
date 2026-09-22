pytest_plugins = ['test_runtime']

from datetime import datetime, timezone
from uuid import uuid4

import psycopg

from app.actual_generation_store import ActualGenerationObservation, ActualGenerationSnapshot, create_or_get_actual_snapshot
from app.actuals_field_mapping import EnergySemantics
from app.forecast_readiness import list_readiness
from app.inverter_connection_request import request_connection
from app.inverter_cloud import InverterCloudProvider
from app.provider_ensemble import ProviderObservation, calibrate
from app.provider_ensemble_store import replace_profile
from app.weather_provider_registry import configure_channel


def test_readiness_is_per_plant_and_advances_only_when_evidence_exists(db):
    request_connection(database_url=db, tenant_id="a", subject="alice", plant_id="002",
                       provider=InverterCloudProvider.DEYE_CLOUD)
    initial = {item.plant_id: item for item in list_readiness(database_url=db, tenant_id="a", subject="alice")}
    assert initial["002"].state == "awaiting_cloud_authorization"
    assert initial["002"].actual_interval_count == 0

    configure_channel(database_url=db, tenant_id="a", subject="alice", provider="google_weather",
                      role="primary", status="configured")
    observation = ActualGenerationObservation(
        provider="manual_deye_export", mapping_version="csv-1", observed_at_utc=datetime(2026, 9, 1, tzinfo=timezone.utc),
        interval_end_utc=datetime(2026, 9, 1, 1, tzinfo=timezone.utc), retrieved_at_utc=datetime(2026, 9, 2, tzinfo=timezone.utc),
        ac_power_kw=3.0, energy_kwh=3.0, energy_semantics=EnergySemantics.INTERVAL,
    )
    create_or_get_actual_snapshot(db, "alice", ActualGenerationSnapshot(
        snapshot_id=uuid4(), tenant_id="a", plant_id="002", source_reference="manual.csv", payload_sha256="a" * 64,
        observation=observation,
    ))
    pending = {item.plant_id: item for item in list_readiness(database_url=db, tenant_id="a", subject="alice")}["002"]
    assert pending.state == "calibration_pending"
    assert pending.configured_provider_count == 1
    assert pending.actual_interval_count == 1

    profile = calibrate(plant_key="002", rated_ac_kw=10, observations=(
        ProviderObservation("002", "google_weather", 3, 2.5),
    ))
    replace_profile(database_url=db, subject="alice", tenant_id="a", profile=profile,
                    calibrated_at_utc=datetime(2026, 9, 2, tzinfo=timezone.utc))
    calibrated = {item.plant_id: item for item in list_readiness(database_url=db, tenant_id="a", subject="alice")}["002"]
    assert calibrated.state == "calibrated"
    assert calibrated.calibrated_provider_count == 1


def test_readiness_is_tenant_isolated(db):
    records = list_readiness(database_url=db, tenant_id="b", subject="bob")
    assert {item.plant_id for item in records} == {"001", "003"}
    try:
        list_readiness(database_url=db, tenant_id="a", subject="bob")
    except PermissionError:
        pass
    else:
        raise AssertionError("cross-tenant readiness must be denied")


