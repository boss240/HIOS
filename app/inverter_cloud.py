"""Read-only contract for inverter-cloud telemetry adapters.

It deliberately contains no HTTP client, vendor SDK, credential value, polling
loop, remote-control method or scheduler.  A production adapter may be added
only after the provider's owner consent, contract, credentials, scope and field
mapping have been approved for a particular tenant and plant.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class InverterCloudProvider(str, Enum):
    DEYE_CLOUD = "deye_cloud"
    FRONIUS_SOLAR_WEB = "fronius_solar_web"
    GOODWE_SEMS = "goodwe_sems"
    GROWATT_SHINESERVER = "growatt_shineserver"
    HUAWEI_FUSIONSOLAR = "huawei_fusionsolar"
    SMA_SUNNY_PORTAL = "sma_sunny_portal"
    SOLAREDGE_ONE = "solaredge_one"
    SOLIS_CLOUD = "solis_cloud"
    SUNGROW_ISOLARCLOUD = "sungrow_isolarcloud"
    VICTRON_VRM = "victron_vrm"


class AccessMethod(str, Enum):
    API_KEY = "api_key"
    CLIENT_CREDENTIALS = "client_credentials"
    OAUTH2_OWNER_CONSENT = "oauth2_owner_consent"
    JWT_ACCESS_TOKEN = "jwt_access_token"
    PARTNER_ACCESS = "partner_access"


@dataclass(frozen=True)
class ProviderProfile:
    provider: InverterCloudProvider
    access_method: AccessMethod
    supports_historical: bool
    supports_live_telemetry: bool
    requires_owner_consent: bool
    implementation_status: str


PROVIDER_PROFILES = {
    InverterCloudProvider.DEYE_CLOUD: ProviderProfile(InverterCloudProvider.DEYE_CLOUD, AccessMethod.PARTNER_ACCESS, True, True, True, "contract_required"),
    InverterCloudProvider.FRONIUS_SOLAR_WEB: ProviderProfile(InverterCloudProvider.FRONIUS_SOLAR_WEB, AccessMethod.API_KEY, True, True, True, "contract_required"),
    InverterCloudProvider.GOODWE_SEMS: ProviderProfile(InverterCloudProvider.GOODWE_SEMS, AccessMethod.CLIENT_CREDENTIALS, True, True, True, "contract_required"),
    InverterCloudProvider.GROWATT_SHINESERVER: ProviderProfile(InverterCloudProvider.GROWATT_SHINESERVER, AccessMethod.PARTNER_ACCESS, False, False, True, "access_verification_required"),
    InverterCloudProvider.HUAWEI_FUSIONSOLAR: ProviderProfile(InverterCloudProvider.HUAWEI_FUSIONSOLAR, AccessMethod.PARTNER_ACCESS, True, True, True, "contract_required"),
    InverterCloudProvider.SMA_SUNNY_PORTAL: ProviderProfile(InverterCloudProvider.SMA_SUNNY_PORTAL, AccessMethod.OAUTH2_OWNER_CONSENT, True, True, True, "contract_required"),
    InverterCloudProvider.SOLAREDGE_ONE: ProviderProfile(InverterCloudProvider.SOLAREDGE_ONE, AccessMethod.OAUTH2_OWNER_CONSENT, True, True, True, "developer_registration_required"),
    InverterCloudProvider.SOLIS_CLOUD: ProviderProfile(InverterCloudProvider.SOLIS_CLOUD, AccessMethod.OAUTH2_OWNER_CONSENT, True, True, True, "sales_qualification_required"),
    InverterCloudProvider.SUNGROW_ISOLARCLOUD: ProviderProfile(InverterCloudProvider.SUNGROW_ISOLARCLOUD, AccessMethod.OAUTH2_OWNER_CONSENT, True, True, True, "developer_registration_required"),
    InverterCloudProvider.VICTRON_VRM: ProviderProfile(InverterCloudProvider.VICTRON_VRM, AccessMethod.JWT_ACCESS_TOKEN, True, True, True, "access_token_required"),
}


@dataclass(frozen=True)
class InverterCloudBinding:
    """A tenant/plant-scoped connection proposal without a secret value."""

    tenant_id: str
    plant_id: str
    provider: InverterCloudProvider
    external_plant_id: str
    credential_reference: str
    consent_record_reference: str
    mapping_version: str
    read_only: bool = True

    def __post_init__(self) -> None:
        for name in ("tenant_id", "plant_id", "external_plant_id", "credential_reference", "consent_record_reference", "mapping_version"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not self.read_only:
            raise ValueError("inverter-cloud bindings must be read-only")


@dataclass(frozen=True)
class InverterTelemetry:
    """Canonical measurement returned by an approved provider adapter."""

    observed_at_utc: datetime
    retrieved_at_utc: datetime
    ac_power_w: float | None
    energy_wh: float | None
    device_status: str | None
    provider: InverterCloudProvider
    external_device_id: str
    source_reference: str
    mapping_version: str

    def __post_init__(self) -> None:
        for name in ("observed_at_utc", "retrieved_at_utc"):
            value = getattr(self, name)
            if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
                raise ValueError(f"{name} must be timezone-aware")
            if value.astimezone(timezone.utc) != value:
                raise ValueError(f"{name} must be UTC")
        for name in ("external_device_id", "source_reference", "mapping_version"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a non-empty string")
        for name in ("ac_power_w", "energy_wh"):
            value = getattr(self, name)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0):
                raise ValueError(f"{name} must be a non-negative number when supplied")


def profile_for(provider: InverterCloudProvider) -> ProviderProfile:
    """Return the fixed first-wave provider profile without network discovery."""
    return PROVIDER_PROFILES[provider]
