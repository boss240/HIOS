"""Fail-closed evaluation release gate; it does not approve or persist policies."""
from __future__ import annotations

from dataclasses import dataclass
import math

from app.forecast_evaluation import EvaluationMetrics


def _non_negative_number(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite non-negative number")
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return result


def _reference(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class ApprovedEvaluationPolicy:
    """An explicit scope-specific policy supplied after ML/QA/Product approval."""

    policy_version: str
    approval_reference: str
    minimum_pair_count: int
    minimum_coverage_pct: float
    maximum_mae_kw: float
    maximum_rmse_kw: float
    maximum_absolute_bias_kw: float
    maximum_nmae_pct: float

    def __post_init__(self) -> None:
        _reference(self.policy_version, "policy_version")
        _reference(self.approval_reference, "approval_reference")
        if isinstance(self.minimum_pair_count, bool) or not isinstance(self.minimum_pair_count, int):
            raise ValueError("minimum_pair_count must be a positive integer")
        if self.minimum_pair_count < 1:
            raise ValueError("minimum_pair_count must be a positive integer")
        coverage = _non_negative_number(self.minimum_coverage_pct, "minimum_coverage_pct")
        if coverage > 100:
            raise ValueError("minimum_coverage_pct must not exceed 100")
        for name in (
            "maximum_mae_kw",
            "maximum_rmse_kw",
            "maximum_absolute_bias_kw",
            "maximum_nmae_pct",
        ):
            _non_negative_number(getattr(self, name), name)


@dataclass(frozen=True)
class EvaluationReleaseDecision:
    accepted: bool
    policy_version: str
    reasons: tuple[str, ...]


def evaluate_release(*, metrics: EvaluationMetrics, coverage_pct: float,
                     policy: ApprovedEvaluationPolicy) -> EvaluationReleaseDecision:
    """Return a reviewable gate decision from metrics and an approved policy.

    The caller supplies coverage from a frozen evaluation population. This
    function has no default policy, no approval side effect and cannot promote
    a model or enable a forecast service.
    """
    coverage = _non_negative_number(coverage_pct, "coverage_pct")
    if coverage > 100:
        raise ValueError("coverage_pct must not exceed 100")

    reasons: list[str] = []
    if metrics.pair_count < policy.minimum_pair_count:
        reasons.append("minimum_pair_count_not_met")
    if coverage < policy.minimum_coverage_pct:
        reasons.append("minimum_coverage_not_met")
    if metrics.mae_kw is None or metrics.mae_kw > policy.maximum_mae_kw:
        reasons.append("mae_limit_not_met")
    if metrics.rmse_kw is None or metrics.rmse_kw > policy.maximum_rmse_kw:
        reasons.append("rmse_limit_not_met")
    if metrics.bias_kw is None or abs(metrics.bias_kw) > policy.maximum_absolute_bias_kw:
        reasons.append("bias_limit_not_met")
    if metrics.nmae_pct is None or metrics.nmae_pct > policy.maximum_nmae_pct:
        reasons.append("nmae_limit_not_met")
    return EvaluationReleaseDecision(not reasons, policy.policy_version, tuple(reasons))
