"""Tenant-safe immutable model candidate registry; approval workflow is separate."""
from dataclasses import dataclass

import psycopg


@dataclass(frozen=True)
class ModelCandidate:
    tenant_id: str
    plant_id: str
    model_id: str
    model_version: str
    model_type: str
    feature_schema_version: str
    configuration_hash: str
    code_commit: str
    training_dataset_ref: str
    artifact_sha256: str | None = None
    evaluation_ref: str | None = None


def register_candidate(database_url: str, subject: str, candidate: ModelCandidate) -> bool:
    """Register a candidate once for an active member's plant; never mutate it."""
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        row = connection.execute(
            """WITH owned_plant AS (
                    SELECT 1 FROM plant p JOIN membership m ON m.tenant_id = p.tenant_id
                    WHERE p.tenant_id = %s AND p.public_id = %s AND m.subject = %s AND m.active
                ), inserted AS (
                    INSERT INTO model_registry (
                        tenant_id, plant_id, model_id, model_version, model_type, state,
                        feature_schema_version, configuration_hash, code_commit, artifact_sha256,
                        training_dataset_ref, evaluation_ref, created_by
                    ) SELECT %s, %s, %s, %s, %s, 'candidate', %s, %s, %s, %s, %s, %s, %s
                    FROM owned_plant
                    ON CONFLICT (tenant_id, plant_id, model_id, model_version) DO NOTHING
                    RETURNING 1
                ) SELECT EXISTS (SELECT 1 FROM owned_plant), EXISTS (SELECT 1 FROM inserted)""",
            (candidate.tenant_id, candidate.plant_id, subject,
             candidate.tenant_id, candidate.plant_id, candidate.model_id, candidate.model_version,
             candidate.model_type, candidate.feature_schema_version, candidate.configuration_hash,
             candidate.code_commit, candidate.artifact_sha256, candidate.training_dataset_ref,
             candidate.evaluation_ref, subject),
        ).fetchone()
        if not row[0]:
            raise PermissionError("Active membership and tenant-owned plant are required")
        return row[1]


def resolve_approved_candidate(database_url: str, subject: str, tenant_id: str, plant_id: str,
                               model_id: str) -> ModelCandidate:
    """Return the latest approved candidate only for an active tenant member."""
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        row = connection.execute(
            """SELECT r.tenant_id, r.plant_id, r.model_id, r.model_version, r.model_type,
                      r.feature_schema_version, r.configuration_hash, r.code_commit,
                      r.training_dataset_ref, r.artifact_sha256, r.evaluation_ref
               FROM model_registry r JOIN membership m ON m.tenant_id = r.tenant_id
               WHERE r.tenant_id = %s AND r.plant_id = %s AND r.model_id = %s
                 AND r.state = 'approved' AND m.subject = %s AND m.active
               ORDER BY r.created_at DESC LIMIT 1""",
            (tenant_id, plant_id, model_id, subject),
        ).fetchone()
        if row is None:
            raise PermissionError("No approved model is available for this tenant-scoped plant")
        return ModelCandidate(*row)
