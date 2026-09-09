import pytest

from app.forecast_evaluation import EvaluationMetrics
from app.forecast_release_gate import ApprovedEvaluationPolicy, evaluate_release


def policy() -> ApprovedEvaluationPolicy:
    return ApprovedEvaluationPolicy(
        policy_version="evaluation-policy-v1",
        approval_reference="ml-qa-product-decision-001",
        minimum_pair_count=100,
        minimum_coverage_pct=95,
        maximum_mae_kw=10,
        maximum_rmse_kw=15,
        maximum_absolute_bias_kw=4,
        maximum_nmae_pct=5,
    )


def metrics(**changes) -> EvaluationMetrics:
    values = {
        "pair_count": 100,
        "mape_pair_count": 90,
        "mae_kw": 9.0,
        "rmse_kw": 14.0,
        "bias_kw": -3.0,
        "mape_pct": 20.0,
        "nmae_pct": 4.0,
    }
    values.update(changes)
    return EvaluationMetrics(**values)


def test_approved_policy_can_accept_complete_eligible_metrics():
    decision = evaluate_release(metrics=metrics(), coverage_pct=96, policy=policy())

    assert decision.accepted is True
    assert decision.policy_version == "evaluation-policy-v1"
    assert decision.reasons == ()


def test_gate_fails_closed_for_missing_metrics_and_coverage():
    decision = evaluate_release(
        metrics=metrics(pair_count=0, mae_kw=None, rmse_kw=None, bias_kw=None, nmae_pct=None),
        coverage_pct=50,
        policy=policy(),
    )

    assert decision.accepted is False
    assert decision.reasons == (
        "minimum_pair_count_not_met",
        "minimum_coverage_not_met",
        "mae_limit_not_met",
        "rmse_limit_not_met",
        "bias_limit_not_met",
        "nmae_limit_not_met",
    )


def test_policy_requires_explicit_approval_and_valid_limits():
    with pytest.raises(ValueError, match="approval_reference"):
        ApprovedEvaluationPolicy("v1", "", 1, 0, 0, 0, 0, 0)
    with pytest.raises(ValueError, match="minimum_coverage_pct"):
        ApprovedEvaluationPolicy("v1", "decision", 1, 101, 0, 0, 0, 0)
    with pytest.raises(ValueError, match="coverage_pct"):
        evaluate_release(metrics=metrics(), coverage_pct=101, policy=policy())
