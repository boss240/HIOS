from datetime import datetime, timezone

import pytest

from app.inverter_cloud import (
    AccessMethod,
    InverterCloudBinding,
    InverterCloudProvider,
    InverterTelemetry,
    profile_for,
)


def test_first_wave_contains_exactly_ten_read_only_provider_profiles():
    assert len(list(InverterCloudProvider)) == 10
    assert profile_for(InverterCloudProvider.SOLAREDGE_ONE).access_method is AccessMethod.OAUTH2_OWNER_CONSENT
    assert profile_for(InverterCloudProvider.GROWATT_SHINESERVER).implementation_status == "access_verification_required"


def test_binding_requires_tenant_plant_consent_and_secret_reference_but_not_secret_value():
    binding = InverterCloudBinding(
        tenant_id="tenant-a", plant_id="plant-a", provider=InverterCloudProvider.DEYE_CLOUD,
        external_plant_id="cloud-plant-1", credential_reference="vault://deye/tenant-a",
        consent_record_reference="consent-2026-01", mapping_version="deye-v1",
    )

    assert binding.read_only is True


def test_binding_rejects_control_enablement():
    with pytest.raises(ValueError, match="read-only"):
        InverterCloudBinding(
            tenant_id="tenant-a", plant_id="plant-a", provider=InverterCloudProvider.DEYE_CLOUD,
            external_plant_id="cloud-plant-1", credential_reference="vault://deye/tenant-a",
            consent_record_reference="consent-2026-01", mapping_version="deye-v1", read_only=False,
        )


def test_telemetry_requires_utc_timestamps_and_non_negative_measurements():
    observed = datetime(2026, 9, 9, 10, tzinfo=timezone.utc)
    telemetry = InverterTelemetry(
        observed_at_utc=observed, retrieved_at_utc=observed, ac_power_w=1200.0,
        energy_wh=5500.0, device_status="normal", provider=InverterCloudProvider.SOLIS_CLOUD,
        external_device_id="inverter-1", source_reference="snapshot-sha256", mapping_version="solis-v1",
    )

    assert telemetry.ac_power_w == 1200.0


def test_telemetry_rejects_negative_energy():
    observed = datetime(2026, 9, 9, 10, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="energy_wh"):
        InverterTelemetry(
            observed_at_utc=observed, retrieved_at_utc=observed, ac_power_w=1.0,
            energy_wh=-1.0, device_status=None, provider=InverterCloudProvider.SMA_SUNNY_PORTAL,
            external_device_id="inverter-1", source_reference="snapshot", mapping_version="sma-v1",
        )
