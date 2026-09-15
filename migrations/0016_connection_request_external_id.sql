-- Optional provider-native ID supplied by the owner before discovery.
ALTER TABLE inverter_cloud_connection_request
    ADD COLUMN external_plant_id text CHECK (external_plant_id IS NULL OR length(trim(external_plant_id)) > 0);
CREATE UNIQUE INDEX inverter_cloud_connection_request_known_external_id
    ON inverter_cloud_connection_request (tenant_id, provider, external_plant_id)
    WHERE external_plant_id IS NOT NULL;