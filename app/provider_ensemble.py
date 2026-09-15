"""Per-plant challenger scoring and deterministic hourly forecast mixing.

The module is pure: callers retain as-issued provider forecasts and measured
generation separately, then pass paired observations here for analysis.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
import math


def _power(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative power value")
    return float(value)


def _name(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True)
class ProviderObservation:
    """One matched forecast/actual pair for exactly one plant and provider."""

    plant_key: str
    provider: str
    actual_kw: float
    predicted_kw: float


@dataclass(frozen=True)
class ProviderScore:
    provider: str
    pair_count: int
    mae_kw: float
    bias_kw: float
    correlation: float | None
    weight: float


@dataclass(frozen=True)
class EnsembleProfile:
    plant_key: str
    rated_ac_kw: float
    scores: tuple[ProviderScore, ...]

    def weights(self) -> dict[str, float]:
        return {score.provider: score.weight for score in self.scores}


def _correlation(actual: list[float], predicted: list[float]) -> float | None:
    if len(actual) < 2:
        return None
    actual_mean = sum(actual) / len(actual)
    predicted_mean = sum(predicted) / len(predicted)
    numerator = sum((a - actual_mean) * (p - predicted_mean) for a, p in zip(actual, predicted))
    actual_ss = sum((a - actual_mean) ** 2 for a in actual)
    predicted_ss = sum((p - predicted_mean) ** 2 for p in predicted)
    if actual_ss == 0 or predicted_ss == 0:
        return None
    return numerator / math.sqrt(actual_ss * predicted_ss)


def calibrate(*, plant_key: str, rated_ac_kw: float,
              observations: tuple[ProviderObservation, ...]) -> EnsembleProfile:
    """Score providers separately for one plant and derive normalized inverse-MAE weights."""
    plant = _name(plant_key, "plant_key")
    rated = _power(rated_ac_kw, "rated_ac_kw")
    if rated <= 0:
        raise ValueError("rated_ac_kw must be positive")
    grouped: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for observation in observations:
        if _name(observation.plant_key, "observation.plant_key") != plant:
            raise ValueError("observations must belong to exactly one plant")
        provider = _name(observation.provider, "provider")
        grouped[provider].append((_power(observation.actual_kw, "actual_kw"),
                                  _power(observation.predicted_kw, "predicted_kw")))
    if not grouped:
        raise ValueError("at least one provider observation is required")
    error_floor = max(rated * 0.01, 0.01)
    raw_scores = []
    for provider in sorted(grouped):
        pairs = grouped[provider]
        actual = [pair[0] for pair in pairs]
        predicted = [pair[1] for pair in pairs]
        errors = [p - a for a, p in pairs]
        mae = sum(abs(error) for error in errors) / len(errors)
        bias = sum(errors) / len(errors)
        raw_scores.append((provider, len(pairs), mae, bias, _correlation(actual, predicted), 1 / (mae + error_floor)))
    total = sum(row[5] for row in raw_scores)
    return EnsembleProfile(
        plant_key=plant,
        rated_ac_kw=rated,
        scores=tuple(ProviderScore(provider, count, mae, bias, correlation, raw / total)
                     for provider, count, mae, bias, correlation, raw in raw_scores),
    )


def mix_hour(*, profile: EnsembleProfile, predictions_kw: dict[str, float]) -> float:
    """Return a weighted forecast only when every calibrated provider is present."""
    weights = profile.weights()
    if set(predictions_kw) != set(weights):
        raise ValueError("predictions must cover exactly the calibrated providers")
    return sum(weights[provider] * _power(predictions_kw[provider], f"{provider} prediction")
               for provider in sorted(weights))
