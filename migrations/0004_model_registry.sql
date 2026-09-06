-- Immutable, plant-scoped model candidates. Promotion is an explicit later workflow.

CREATE TABLE model_registry (
    tenant_id text NOT NULL,
    plant_id text NOT NULL,
    model_id text NOT NULL CHECK (length(trim(model_id)) > 0),
    model_version text NOT NULL CHECK (length(trim(model_version)) > 0),
    model_type text NOT NULL CHECK (length(trim(model_type)) > 0),
    state text NOT NULL CHECK (state IN ('candidate', 'approved', 'active', 'deprecated', 'retired')),
    feature_schema_version text NOT NULL CHECK (length(trim(feature_schema_version)) > 0),
    configuration_hash text NOT NULL CHECK (configuration_hash ~ '^[0-9a-f]{64}$'),
    code_commit text NOT NULL CHECK (code_commit ~ '^[0-9a-f]{7,64}$'),
    artifact_sha256 text CHECK (artifact_sha256 IS NULL OR artifact_sha256 ~ '^[0-9a-f]{64}$'),
    training_dataset_ref text NOT NULL CHECK (length(trim(training_dataset_ref)) > 0),
    evaluation_ref text,
    created_by text NOT NULL CHECK (length(trim(created_by)) > 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    approved_by text,
    approved_at timestamptz,
    decision_ref text,
    PRIMARY KEY (tenant_id, plant_id, model_id, model_version),
    FOREIGN KEY (tenant_id, plant_id) REFERENCES plant (tenant_id, public_id),
    CHECK ((approved_by IS NULL AND approved_at IS NULL AND decision_ref IS NULL) OR
           (approved_by IS NOT NULL AND approved_at IS NOT NULL AND decision_ref IS NOT NULL))
);

CREATE INDEX model_registry_approved_lookup ON model_registry
    (tenant_id, plant_id, model_id, state, created_at DESC);
