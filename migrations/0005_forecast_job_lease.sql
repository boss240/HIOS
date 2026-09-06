-- A short-lived, tenant-scoped lease prevents duplicate scheduled job execution.

CREATE TABLE forecast_job_lease (
    tenant_id text NOT NULL,
    plant_id text NOT NULL,
    forecast_origin_utc timestamptz NOT NULL,
    horizon_id text NOT NULL CHECK (horizon_id IN ('intraday', 'day_ahead')),
    lease_id uuid NOT NULL,
    claimed_by text NOT NULL CHECK (length(trim(claimed_by)) > 0),
    expires_at timestamptz NOT NULL,
    claimed_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, plant_id, forecast_origin_utc, horizon_id),
    FOREIGN KEY (tenant_id, plant_id) REFERENCES plant (tenant_id, public_id)
);

CREATE INDEX forecast_job_lease_expiry ON forecast_job_lease (expires_at);
