-- A safe pre-discovery request to connect one plant to an inverter cloud.
-- No credential, token, API payload or native cloud ID is retained at this stage.
CREATE TABLE inverter_cloud_connection_request (
    request_id uuid PRIMARY KEY,
    tenant_id text NOT NULL REFERENCES tenant(id),
    plant_id text NOT NULL REFERENCES plant(public_id) ON DELETE CASCADE,
    provider text NOT NULL CHECK (length(trim(provider)) > 0),
    status text NOT NULL DEFAULT 'awaiting_authorization' CHECK (status IN ('awaiting_authorization', 'discovery_pending', 'verified', 'blocked')),
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, plant_id, provider)
);
CREATE INDEX inverter_cloud_connection_request_tenant_plant
    ON inverter_cloud_connection_request (tenant_id, plant_id, provider);