from datetime import datetime, timezone
from uuid import UUID

import pytest

from app.actuals_alignment import AlignedPowerSample
from app.frozen_evaluation_evidence import FrozenEvaluationEvidence
from app.frozen_evaluation_report import build_frozen_evaluation_report


UTC = timezone.utc
HASH = "a" * 64


def evidence(**changes) -> FrozenEvaluationEvidence:
    values = {
        "evidence_version": "evaluation-evidence-v1",
        "dataset_sha256": HASH,
        "forecast_snapshot_sha256": "b" * 64,
        "actuals_snapshot_sha256": "c" * 64,
        "exclusions_sha256": "d" * 64,
        "actual_provider": "deye",
        "actual_mapping_version": "deye-v1",
        "holdout_start_utc": datetime(2026, 1, 1, tzinfo=UTC),
        "holdout_end_utc": datetime(2026, 1, 2, tzinfo=UTC),
        "actuals_as_of_utc": datetime(2026, 1, 3, tzinfo=UTC),
        "expected_target_count": 3,
        "included_pair_count": 2,
        "excluded_counts": {"missing_actual": 1},
    }
    values.update(changes)
    return FrozenEvaluationEvidence(**values)


def sample(hour: int, actual: float, predicted: float) -> AlignedPowerSample:
    start = datetime(2026, 1, 1, hour, tzinfo=UTC)
    return AlignedPowerSample(start, start.replace(hour=hour + 1), predicted, actual, UUID(int=hour + 1))


def test_report_calculates_metrics_for_frozen_pairs():
    report = build_frozen_evaluation_report(
        evidence=evidence(),
        samples=(sample(10, 100, 110), sample(11, 50, 40)),
        rated_ac_kw=100,
        is_daylight=lambda start: start.hour >= 10,
    )
    assert report.metrics.pair_count == 2
    assert report.metrics.mape_pair_count == 2
    assert report.metrics.mae_kw == 10
    assert report.evidence.coverage_pct == pytest.approx(66.6666667)


def test_report_rejects_population_or_interval_mismatch():
    with pytest.raises(ValueError, match="sample count"):
        build_frozen_evaluation_report(
            evidence=evidence(), samples=(sample(10, 1, 1),), rated_ac_kw=100, is_daylight=lambda _: True,
        )
    with pytest.raises(ValueError, match="unique exact intervals"):
        build_frozen_evaluation_report(
            evidence=evidence(), samples=(sample(10, 1, 1), sample(10, 1, 1)),
            rated_ac_kw=100, is_daylight=lambda _: True,
        )

