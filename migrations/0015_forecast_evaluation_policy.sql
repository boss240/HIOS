-- Explicit, versioned forecast-evaluation thresholds. No default target is assumed.
CREATE TABLE forecast_evaluation_policy (
    tenant_id text NOT NULL REFERENCES tenant(id),
    plant_id text NOT NULL REFERENCES plant(public_id) ON DELETE CASCADE,
    policy_version text NOT NULL CHECK (length(trim(policy_version)) > 0),
    max_mae_kw double precision NOT NULL CHECK (max_mae_kw > 0 AND max_mae_kw < 'Infinity'::double precision),
    max_nmae_percent double precision NOT NULL CHECK (max_nmae_percent > 0 AND max_nmae_percent <= 100),
    max_daylight_mape_percent double precision NOT NULL CHECK (max_daylight_mape_percent > 0 AND max_daylight_mape_percent <= 100),
    min_eligible_pairs integer NOT NULL CHECK (min_eligible_pairs > 0),
    approved_by text NOT NULL CHECK (length(trim(approved_by)) > 0),
    approved_at_utc timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, plant_id, policy_version)
);
CREATE INDEX forecast_evaluation_policy_latest
    ON forecast_evaluation_policy (tenant_id, plant_id, approved_at_utc DESC);