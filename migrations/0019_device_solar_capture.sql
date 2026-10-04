CREATE TABLE device_solar_capture (
    capture_id uuid PRIMARY KEY,
    tenant_id text NOT NULL,
    plant_id text NOT NULL,
    device_sha256 text NOT NULL CHECK (device_sha256 ~ '^[0-9a-f]{64}$'),
    day_utc date NOT NULL,
    retrieved_at_utc timestamptz NOT NULL,
    document_sha256 text NOT NULL CHECK (document_sha256 ~ '^[0-9a-f]{64}$'),
    document jsonb NOT NULL CHECK (jsonb_typeof(document)='object'),
    FOREIGN KEY (tenant_id,plant_id) REFERENCES plant(tenant_id,public_id),
    UNIQUE(tenant_id,plant_id,device_sha256,day_utc,document_sha256)
);
CREATE TRIGGER device_solar_capture_no_update BEFORE UPDATE
    ON device_solar_capture FOR EACH ROW
    EXECUTE FUNCTION prevent_provider_forecast_capture_update();
