-- Preserve interval versus cumulative source meaning for normalized actual energy.

ALTER TABLE actual_generation_snapshot
    ADD COLUMN energy_semantics text;

ALTER TABLE actual_generation_snapshot
    ADD CONSTRAINT actual_generation_snapshot_energy_semantics_check CHECK (
        (energy_kwh IS NULL AND energy_semantics IS NULL)
        OR (energy_kwh IS NOT NULL AND energy_semantics IN ('interval', 'cumulative'))
    );
