-- Field-level source lineage for composed operational weather inputs.

ALTER TABLE weather_snapshot
    ADD COLUMN provider_provenance jsonb NOT NULL DEFAULT '{}'::jsonb
    CHECK (jsonb_typeof(provider_provenance) = 'object');
