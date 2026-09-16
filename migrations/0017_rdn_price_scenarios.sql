CREATE TABLE rdn_price_scenario (
    scenario_id uuid PRIMARY KEY,
    tenant_id text NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    name text NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 120),
    source_reference text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, name)
);

CREATE TABLE rdn_price_point (
    scenario_id uuid NOT NULL REFERENCES rdn_price_scenario(scenario_id) ON DELETE CASCADE,
    interval_start_utc timestamptz NOT NULL,
    price_uah_per_kwh numeric NOT NULL CHECK (price_uah_per_kwh >= 0),
    PRIMARY KEY (scenario_id, interval_start_utc)
);
CREATE INDEX rdn_price_scenario_tenant_created ON rdn_price_scenario (tenant_id, created_at DESC);
