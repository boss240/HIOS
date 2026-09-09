-- An approved lifecycle state requires immutable approval evidence.

ALTER TABLE model_registry
    ADD CONSTRAINT model_registry_approved_state_requires_evidence
    CHECK (
        state = 'candidate' OR
        (approved_by IS NOT NULL AND approved_at IS NOT NULL AND decision_ref IS NOT NULL)
    );
