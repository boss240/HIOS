-- Tenant-scoped, immutable measured-generation inputs for evaluation and calibration.

CREATE TABLE actual_generation_snapshot (
    snapshot_id uuid PRIMARY KEY,
    tenant_id text NOT NULL,
    plant_id text NOT NULL,
    provider text NOT NULL CHECK (length(trim(provider)) > 0),
    mapping_version text NOT NULL CHECK (length(trim(mapping_version)) > 0),
    observed_at_utc timestamptz NOT NULL,
    interval_end_utc timestamptz NOT NULL CHECK (interval_end_utc > observed_at_utc),
    retrieved_at_utc timestamptz NOT NULL CHECK (retrieved_at_utc >= observed_at_utc),
    source_reference text NOT NULL CHECK (length(trim(source_reference)) > 0),
    payload_sha256 text NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    ac_power_kw double precision CHECK (
        ac_power_kw IS NULL OR (ac_power_kw >= 0 AND ac_power_kw < 'Infinity'::double precision)
    ),
    energy_kwh double precision CHECK (
        energy_kwh IS NULL OR (energy_kwh >= 0 AND energy_kwh < 'Infinity'::double precision)
    ),
    device_status text,
    quality_flags jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(quality_flags) = 'array'),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id, plant_id) REFERENCES plant (tenant_id, public_id),
    CHECK (ac_power_kw IS NOT NULL OR energy_kwh IS NOT NULL),
    UNIQUE (tenant_id, plant_id, provider, mapping_version, observed_at_utc,
            interval_end_utc, payload_sha256)
);

CREATE INDEX actual_generation_snapshot_tenant_plant_observed
    ON actual_generation_snapshot (tenant_id, plant_id, observed_at_utc, retrieved_at_utc DESC);
