-- Tenant-scoped, immutable normalized inputs for forecast provenance.

CREATE TABLE weather_snapshot (
    snapshot_id uuid PRIMARY KEY,
    tenant_id text NOT NULL,
    plant_id text NOT NULL,
    provider text NOT NULL CHECK (length(trim(provider)) > 0),
    product text NOT NULL CHECK (length(trim(product)) > 0),
    mapping_version text NOT NULL CHECK (length(trim(mapping_version)) > 0),
    provider_issued_at_utc timestamptz NOT NULL,
    valid_at_utc timestamptz NOT NULL,
    interval_end_utc timestamptz NOT NULL CHECK (interval_end_utc > valid_at_utc),
    retrieved_at_utc timestamptz NOT NULL,
    source_reference text NOT NULL CHECK (length(trim(source_reference)) > 0),
    payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    irradiance_global_wm2 double precision NOT NULL CHECK (
        irradiance_global_wm2 >= 0 AND irradiance_global_wm2 < 'Infinity'::double precision
    ),
    cloud_cover_pct double precision NOT NULL CHECK (cloud_cover_pct BETWEEN 0 AND 100),
    temperature_c double precision NOT NULL CHECK (
        temperature_c > '-Infinity'::double precision AND temperature_c < 'Infinity'::double precision
    ),
    wind_speed_ms double precision CHECK (
        wind_speed_ms >= 0 AND wind_speed_ms < 'Infinity'::double precision
    ),
    irradiance_direct_wm2 double precision CHECK (
        irradiance_direct_wm2 >= 0 AND irradiance_direct_wm2 < 'Infinity'::double precision
    ),
    irradiance_diffuse_wm2 double precision CHECK (
        irradiance_diffuse_wm2 >= 0 AND irradiance_diffuse_wm2 < 'Infinity'::double precision
    ),
    relative_humidity_pct double precision CHECK (relative_humidity_pct BETWEEN 0 AND 100),
    precipitation_mm double precision CHECK (
        precipitation_mm >= 0 AND precipitation_mm < 'Infinity'::double precision
    ),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id, plant_id) REFERENCES plant (tenant_id, public_id),
    UNIQUE (tenant_id, plant_id, provider, product, mapping_version,
            provider_issued_at_utc, valid_at_utc, payload_sha256)
);

CREATE INDEX weather_snapshot_tenant_plant_valid ON weather_snapshot
    (tenant_id, plant_id, valid_at_utc, provider_issued_at_utc DESC);
