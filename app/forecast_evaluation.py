"""Deterministic, threshold-free accuracy metrics for paired AC-power samples."""
from dataclasses import dataclass
import math


def _power(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative AC power value")
    return float(value)


@dataclass(frozen=True)
class EvaluationSample:
    actual_kw: float
    predicted_kw: float
    daylight: bool


@dataclass(frozen=True)
class EvaluationMetrics:
    pair_count: int
    mape_pair_count: int
    mae_kw: float | None
    rmse_kw: float | None
    bias_kw: float | None
    mape_pct: float | None
    nmae_pct: float | None


def evaluate(samples: tuple[EvaluationSample, ...], rated_ac_kw: float) -> EvaluationMetrics:
    """Return metrics or explicit not-evaluated values for zero eligible pairs."""
    rated = _power(rated_ac_kw, "rated_ac_kw")
    if rated <= 0:
        raise ValueError("rated_ac_kw must be positive")
    epsilon = rated * 0.01
    errors = []
    mape_terms = []
    for sample in samples:
        actual = _power(sample.actual_kw, "actual_kw")
        predicted = _power(sample.predicted_kw, "predicted_kw")
        error = predicted - actual
        errors.append(error)
        if sample.daylight and actual > epsilon:
            mape_terms.append(abs(error) / actual)
    if not errors:
        return EvaluationMetrics(0, 0, None, None, None, None, None)
    mae = sum(abs(error) for error in errors) / len(errors)
    rmse = math.sqrt(sum(error ** 2 for error in errors) / len(errors))
    bias = sum(errors) / len(errors)
    mape = 100 * sum(mape_terms) / len(mape_terms) if mape_terms else None
    return EvaluationMetrics(len(errors), len(mape_terms), mae, rmse, bias, mape, 100 * mae / rated)
