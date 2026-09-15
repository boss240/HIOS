from datetime import date

import pytest

from app.inverter_cloud import InverterCloudBinding, InverterCloudProvider
from app.plant_onboarding import PlantProfileInput, add_read_only_binding, create_plant, get_onboarding

pytest_plugins = ["test_runtime"]


def test_creates_manual_plant_profile_and_only_metadata_binding(db):
    plant_id = create_plant(
        database_url=db, subject="alice", tenant_id="a", name="New solar site", capacity_kw=42,
        profile=PlantProfileInput(latitude=50.1, longitude=30.2, timezone_name="Europe/Kyiv",
                                  capacity_ac_kw=35, tilt_deg=25, azimuth_deg=180,
                                  meter_boundary="grid export", commissioning_date=date(2026, 1, 1)),
    )
    binding = InverterCloudBinding(
        tenant_id="a", plant_id=plant_id, provider=InverterCloudProvider.DEYE_CLOUD,
        external_plant_id="native-id-in-vault-evidence", credential_reference="keyvault://deye/a",
        consent_record_reference="consent-a-001", mapping_version="deye-v1",
    )
    add_read_only_binding(database_url=db, subject="alice", binding=binding, discovery_status="verified")
    data = get_onboarding(database_url=db, subject="alice", tenant_id="a", plant_id=plant_id)
    assert data["name"] == "New solar site"
    assert data["cloudBindings"] == [{"provider": "deye_cloud", "externalPlantId": "native-id-in-vault-evidence", "credentialReference": "keyvault://deye/a", "consentRecordReference": "consent-a-001", "mappingVersion": "deye-v1", "readOnly": True, "discoveryStatus": "verified"}]


def test_onboarding_is_tenant_safe_and_rejects_invalid_manual_ranges(db):
    with pytest.raises(PermissionError):
        create_plant(database_url=db, subject="bob", tenant_id="a", name="Forbidden", capacity_kw=None,
                     profile=PlantProfileInput())
    with pytest.raises(ValueError, match="latitude"):
        create_plant(database_url=db, subject="alice", tenant_id="a", name="Bad", capacity_kw=None,
                     profile=PlantProfileInput(latitude=91))