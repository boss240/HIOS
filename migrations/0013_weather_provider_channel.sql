-- Tenant-scoped configuration of forecast-provider channels.
-- This is metadata only: endpoint credentials and live polling are intentionally excluded.
CREATE TABLE weather_provider_channel (
    tenant_id text NOT NULL REFERENCES tenant(id),
    provider text NOT NULL CHECK (length(trim(provider)) > 0),
    role text NOT NULL CHECK (role IN ('primary', 'challenger', 'research')),
    status text NOT NULL DEFAULT 'candidate' CHECK (status IN ('candidate', 'configured', 'disabled')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, provider)
);
CREATE INDEX weather_provider_channel_tenant_status
    ON weather_provider_channel (tenant_id, status, provider COLLATE "C");