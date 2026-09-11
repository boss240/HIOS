"""Immutable input contract for a reproducible forecast evaluation.

This module contains no provider access, database writes or numeric release
limits. It makes the evidence required by a later release decision explicit.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Mapping


_SHA256 = re.compile(r"[0-9a-f]{64}")


def _text(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _sha256(value: str, name: str) -> str:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    return value


def _utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise ValueError(f"{name} must be a UTC datetime")
    return value


def _count(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


@dataclass(frozen=True)
class FrozenEvaluationEvidence:
    """Hashes and counts for one chronological frozen holdout evaluation."""

    evidence_version: str
    dataset_sha256: str
    forecast_snapshot_sha256: str
    actuals_snapshot_sha256: str
    exclusions_sha256: str
    actual_provider: str
    actual_mapping_version: str
    holdout_start_utc: datetime
    holdout_end_utc: datetime
    actuals_as_of_utc: datetime
    expected_target_count: int
    included_pair_count: int
    excluded_counts: Mapping[str, int]

    def __post_init__(self) -> None:
        for name in ("evidence_version", "actual_provider", "actual_mapping_version"):
            _text(getattr(self, name), name)
        for name in (
            "dataset_sha256", "forecast_snapshot_sha256", "actuals_snapshot_sha256", "exclusions_sha256",
        ):
            _sha256(getattr(self, name), name)
        start = _utc(self.holdout_start_utc, "holdout_start_utc")
        end = _utc(self.holdout_end_utc, "holdout_end_utc")
        cutoff = _utc(self.actuals_as_of_utc, "actuals_as_of_utc")
        if start >= end:
            raise ValueError("holdout_start_utc must precede holdout_end_utc")
        if cutoff < end:
            raise ValueError("actuals_as_of_utc must not precede holdout_end_utc")
        expected = _count(self.expected_target_count, "expected_target_count")
        included = _count(self.included_pair_count, "included_pair_count")
        if not self.excluded_counts:
            raise ValueError("excluded_counts must record the evaluated population")
        excluded = 0
        for reason, count in self.excluded_counts.items():
            _text(reason, "excluded_counts key")
            excluded += _count(count, f"excluded_counts[{reason}]")
        if expected != included + excluded:
            raise ValueError("expected_target_count must equal included and excluded counts")

    @property
    def coverage_pct(self) -> float:
        """Coverage across the predeclared evaluation population."""
        if self.expected_target_count == 0:
            return 0.0
        return 100 * self.included_pair_count / self.expected_target_count
