from datetime import datetime, timezone

import pytest

from app.forecast_evaluation import EvaluationMetrics
from app.forecast_release_gate import ApprovedEvaluationPolicy, evaluate_frozen_release
from app.frozen_evaluation_evidence import FrozenEvaluationEvidence


def evidence(**changes) -> FrozenEvaluationEvidence:
    values = {
        "evidence_version": "holdout-evidence-v1",
        "dataset_sha256": "a" * 64,
        "forecast_snapshot_sha256": "b" * 64,
        "actuals_snapshot_sha256": "c" * 64,
        "exclusions_sha256": "d" * 64,
        "actual_provider": "deye_cloud",
        "actual_mapping_version": "deye-actuals-v1",
        "holdout_start_utc": datetime(2026, 9, 1, tzinfo=timezone.utc),
        "holdout_end_utc": datetime(2026, 9, 2, tzinfo=timezone.utc),
        "actuals_as_of_utc": datetime(2026, 9, 3, tzinfo=timezone.utc),
        "expected_target_count": 10,
        "included_pair_count": 8,
        "excluded_counts": {"missing_actual": 2},
    }
    values.update(changes)
    return FrozenEvaluationEvidence(**values)


def metrics(**changes) -> EvaluationMetrics:
    values = {"pair_count": 8, "mape_pair_count": 7, "mae_kw": 1.0,
              "rmse_kw": 1.5, "bias_kw": 0.1, "mape_pct": 5.0, "nmae_pct": 2.0}
    values.update(changes)
    return EvaluationMetrics(**values)


def policy() -> ApprovedEvaluationPolicy:
    return ApprovedEvaluationPolicy("policy-v1", "decision-1", 8, 75, 2, 2, 1, 3)


def test_evidence_requires_complete_frozen_population_and_calculates_coverage():
    assert evidence().coverage_pct == 80.0
    with pytest.raises(ValueError, match="expected_target_count"):
        evidence(expected_target_count=9)
    with pytest.raises(ValueError, match="actuals_as_of"):
        evidence(actuals_as_of_utc=datetime(2026, 9, 1, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="dataset_sha256"):
        evidence(dataset_sha256="not-a-hash")


def test_frozen_gate_uses_evidence_coverage_and_rejects_mismatched_metrics():
    assert evaluate_frozen_release(metrics=metrics(), policy=policy(), evidence=evidence()).accepted
    with pytest.raises(ValueError, match="pair_count"):
        evaluate_frozen_release(metrics=metrics(pair_count=7), policy=policy(), evidence=evidence())
