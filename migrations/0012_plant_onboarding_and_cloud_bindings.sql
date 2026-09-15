-- Manual plant passport data and read-only cloud bindings.
-- Credentials, tokens, raw API payloads and device-control permissions are never stored here.

CREATE TABLE plant_profile (
    plant_id text PRIMARY KEY REFERENCES plant(public_id) ON DELETE CASCADE,
    latitude double precision CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
    longitude double precision CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
    timezone_name text,
    capacity_ac_kw double precision CHECK (capacity_ac_kw IS NULL OR (capacity_ac_kw >= 0 AND capacity_ac_kw < 'Infinity'::double precision)),
    tilt_deg double precision CHECK (tilt_deg IS NULL OR tilt_deg BETWEEN 0 AND 90),
    azimuth_deg double precision CHECK (azimuth_deg IS NULL OR azimuth_deg >= 0 AND azimuth_deg < 360),
    mounting_type text,
    meter_boundary text,
    commissioning_date date,
    operator_notes text,
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE inverter_cloud_binding (
    binding_id uuid PRIMARY KEY,
    tenant_id text NOT NULL REFERENCES tenant(id),
    plant_id text NOT NULL REFERENCES plant(public_id) ON DELETE CASCADE,
    provider text NOT NULL CHECK (length(trim(provider)) > 0),
    external_plant_id text NOT NULL CHECK (length(trim(external_plant_id)) > 0),
    credential_reference text NOT NULL CHECK (length(trim(credential_reference)) > 0),
    consent_record_reference text NOT NULL CHECK (length(trim(consent_record_reference)) > 0),
    mapping_version text NOT NULL CHECK (length(trim(mapping_version)) > 0),
    read_only boolean NOT NULL DEFAULT true CHECK (read_only),
    discovery_status text NOT NULL DEFAULT 'pending' CHECK (discovery_status IN ('pending', 'verified', 'blocked')),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, plant_id, provider, external_plant_id)
);

CREATE INDEX inverter_cloud_binding_tenant_plant
    ON inverter_cloud_binding (tenant_id, plant_id, provider);