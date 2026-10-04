-- Source-specific forecasts, preserving receipt and optional provider issue time.
CREATE TABLE provider_forecast_capture (
    capture_id uuid PRIMARY KEY,
    tenant_id text NOT NULL,
    plant_id text NOT NULL,
    provider text NOT NULL CHECK (provider IN ('google_weather','solcast','open_meteo')),
    mapping_version text NOT NULL,
    captured_at_utc timestamptz NOT NULL,
    provider_issued_at_utc timestamptz CHECK (provider_issued_at_utc <= captured_at_utc),
    document_sha256 text NOT NULL CHECK (document_sha256 ~ '^[0-9a-f]{64}$'),
    document jsonb NOT NULL CHECK (jsonb_typeof(document) = 'object'),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id,plant_id) REFERENCES plant(tenant_id,public_id),
    UNIQUE (tenant_id,plant_id,document_sha256)
);
CREATE INDEX provider_forecast_capture_scope ON provider_forecast_capture
    (tenant_id,plant_id,provider,captured_at_utc);
CREATE FUNCTION prevent_provider_forecast_capture_update() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN
    RAISE EXCEPTION 'provider forecast captures cannot be rewritten';
END $$;
CREATE TRIGGER provider_forecast_capture_no_update BEFORE UPDATE
    ON provider_forecast_capture FOR EACH ROW
    EXECUTE FUNCTION prevent_provider_forecast_capture_update();
