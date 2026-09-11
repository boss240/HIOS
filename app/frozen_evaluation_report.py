"""Pure, reproducible report assembly for frozen forecast evaluation inputs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from app.actuals_alignment import AlignedPowerSample
from app.forecast_evaluation import EvaluationMetrics, EvaluationSample, evaluate
from app.frozen_evaluation_evidence import FrozenEvaluationEvidence


@dataclass(frozen=True)
class FrozenEvaluationReport:
    """Metrics bound to an already-frozen input population.

    This report performs no database or provider access.  It cannot freeze data,
    approve thresholds, promote a model, or claim real-world accuracy.
    """

    evidence: FrozenEvaluationEvidence
    metrics: EvaluationMetrics


def build_frozen_evaluation_report(*, evidence: FrozenEvaluationEvidence,
                                   samples: tuple[AlignedPowerSample, ...],
                                   rated_ac_kw: float,
                                   is_daylight: Callable[[datetime], bool]) -> FrozenEvaluationReport:
    """Calculate metrics only for the exact, declared frozen population.

    ``samples`` must already be exact-interval, as-of-safe pairs from
    ``load_aligned_power_samples``.  The daylight classifier is explicit so this
    module cannot infer solar context or silently alter the evaluation segment.
    """
    if not callable(is_daylight):
        raise ValueError("is_daylight must be callable")
    if len(samples) != evidence.included_pair_count:
        raise ValueError("sample count must equal frozen evidence included_pair_count")

    intervals: set[tuple[datetime, datetime]] = set()
    metric_samples: list[EvaluationSample] = []
    for sample in samples:
        interval = (sample.interval_start_utc, sample.interval_end_utc)
        if interval in intervals:
            raise ValueError("samples must contain unique exact intervals")
        intervals.add(interval)
        metric_samples.append(EvaluationSample(
            actual_kw=sample.actual_power_kw,
            predicted_kw=sample.predicted_power_kw,
            daylight=bool(is_daylight(sample.interval_start_utc)),
        ))

    metrics = evaluate(tuple(metric_samples), rated_ac_kw)
    if metrics.pair_count != evidence.included_pair_count:
        raise ValueError("metrics pair_count must equal frozen evidence included_pair_count")
    return FrozenEvaluationReport(evidence=evidence, metrics=metrics)
