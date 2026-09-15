-- Latest evaluated challenger profile for each tenant-scoped plant.
-- Source forecasts and actuals remain in their respective immutable stores.

CREATE TABLE provider_ensemble_profile (
    tenant_id text NOT NULL,
    plant_id text NOT NULL,
    provider text NOT NULL CHECK (length(trim(provider)) > 0),
    pair_count integer NOT NULL CHECK (pair_count > 0),
    mae_kw double precision NOT NULL CHECK (mae_kw >= 0 AND mae_kw < 'Infinity'::double precision),
    bias_kw double precision NOT NULL CHECK (bias_kw > '-Infinity'::double precision AND bias_kw < 'Infinity'::double precision),
    correlation double precision CHECK (correlation IS NULL OR (correlation >= -1 AND correlation <= 1)),
    weight double precision NOT NULL CHECK (weight > 0 AND weight <= 1),
    calibrated_at_utc timestamptz NOT NULL,
    PRIMARY KEY (tenant_id, plant_id, provider),
    FOREIGN KEY (tenant_id, plant_id) REFERENCES plant (tenant_id, public_id)
);

CREATE INDEX provider_ensemble_profile_lookup
    ON provider_ensemble_profile (tenant_id, plant_id, calibrated_at_utc DESC);
