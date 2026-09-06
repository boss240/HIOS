-- Minimal auditable outcomes for controlled worker attempts; no payloads or secrets.

CREATE TABLE forecast_job_outcome (
    outcome_id uuid PRIMARY KEY,
    lease_id uuid NOT NULL UNIQUE,
    tenant_id text NOT NULL,
    plant_id text NOT NULL,
    forecast_origin_utc timestamptz NOT NULL,
    horizon_id text NOT NULL CHECK (horizon_id IN ('intraday', 'day_ahead')),
    status text NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    claimed_by text NOT NULL CHECK (length(trim(claimed_by)) > 0),
    started_at timestamptz NOT NULL DEFAULT now(),
    completed_at timestamptz,
    forecast_run_id uuid REFERENCES forecast_run(run_id) ON DELETE RESTRICT,
    published_points integer CHECK (published_points IS NULL OR published_points >= 0),
    error_class text,
    FOREIGN KEY (tenant_id, plant_id) REFERENCES plant (tenant_id, public_id),
    CHECK ((status = 'running' AND completed_at IS NULL AND forecast_run_id IS NULL
            AND published_points IS NULL AND error_class IS NULL) OR
           (status = 'succeeded' AND completed_at IS NOT NULL AND forecast_run_id IS NOT NULL
            AND published_points IS NOT NULL AND error_class IS NULL) OR
           (status = 'failed' AND completed_at IS NOT NULL AND forecast_run_id IS NULL
            AND published_points IS NULL AND error_class IS NOT NULL))
);

CREATE INDEX forecast_job_outcome_scope_time ON forecast_job_outcome
    (tenant_id, plant_id, forecast_origin_utc DESC);
