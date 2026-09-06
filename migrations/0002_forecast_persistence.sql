-- Sprint 2 forecast runs are tenant-scoped, versioned and append-only.
-- New applications must use the logical key below for retry idempotency.

ALTER TABLE plant
    ADD CONSTRAINT plant_tenant_public_id_unique UNIQUE (tenant_id, public_id);

CREATE TABLE forecast_run (
    run_id uuid PRIMARY KEY,
    tenant_id text NOT NULL,
    plant_id text NOT NULL,
    forecast_origin_utc timestamptz NOT NULL,
    horizon_id text NOT NULL CHECK (horizon_id IN ('intraday', 'day_ahead')),
    model_id text NOT NULL CHECK (length(trim(model_id)) > 0),
    model_version text NOT NULL CHECK (length(trim(model_version)) > 0),
    feature_version text NOT NULL CHECK (length(trim(feature_version)) > 0),
    input_hash text NOT NULL CHECK (input_hash ~ '^[0-9a-f]{64}$'),
    configuration_hash text NOT NULL CHECK (configuration_hash ~ '^[0-9a-f]{64}$'),
    code_commit text NOT NULL CHECK (code_commit ~ '^[0-9a-f]{7,64}$'),
    status text NOT NULL CHECK (status IN ('normal', 'degraded', 'blocked')),
    quality_flags jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(quality_flags) = 'array'),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id, plant_id) REFERENCES plant (tenant_id, public_id),
    UNIQUE (tenant_id, plant_id, forecast_origin_utc, horizon_id, model_id,
            model_version, input_hash)
);

CREATE INDEX forecast_run_tenant_plant_origin ON forecast_run
    (tenant_id, plant_id, forecast_origin_utc DESC);

CREATE TABLE forecast_point (
    run_id uuid NOT NULL REFERENCES forecast_run(run_id) ON DELETE RESTRICT,
    interval_start_utc timestamptz NOT NULL,
    interval_end_utc timestamptz NOT NULL,
    predicted_power_kw double precision NOT NULL CHECK (
        predicted_power_kw >= 0 AND predicted_power_kw < 'Infinity'::double precision
    ),
    predicted_energy_kwh double precision NOT NULL CHECK (
        predicted_energy_kwh >= 0 AND predicted_energy_kwh < 'Infinity'::double precision
    ),
    quality_flags jsonb NOT NULL DEFAULT '[]'::jsonb CHECK (jsonb_typeof(quality_flags) = 'array'),
    provider_provenance jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(provider_provenance) = 'object'),
    PRIMARY KEY (run_id, interval_start_utc),
    CHECK (interval_end_utc > interval_start_utc)
);
