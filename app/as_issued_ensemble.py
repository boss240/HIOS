"""Score weather-provider forecasts only on comparable as-issued hourly evidence.

This is a pure calibration gate.  It does not retrieve weather, read actuals
from a provider, persist a profile, or choose a production provider.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from app.provider_ensemble import EnsembleProfile, ProviderObservation, calibrate


@dataclass(frozen=True)
class AsIssuedProviderPair:
    """A forecast captured before a target hour and one matched actual value."""

    plant_key: str
    provider: str
    issued_at_utc: datetime
    target_at_utc: datetime
    actual_kw: float
    predicted_kw: float
    daylight: bool
    quality_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class AsIssuedScorecard:
    """Reproducible evidence summary for a per-plant provider comparison."""

    profile: EnsembleProfile
    candidate_hours: int
    eligible_hours: int
    excluded_hours: tuple[tuple[str, int], ...]


def _utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value.astimezone(timezone.utc)


def _name(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _hour_start(value: datetime, name: str) -> datetime:
    result = _utc(value, name)
    if result.minute or result.second or result.microsecond:
        raise ValueError(f"{name} must be aligned to an hourly UTC boundary")
    return result


def score_as_issued(*, plant_key: str, rated_ac_kw: float,
                    pairs: Iterable[AsIssuedProviderPair]) -> AsIssuedScorecard:
    """Calibrate providers only where every candidate has comparable evidence.

    A target hour is eligible only when every observed provider supplied exactly
    one daylight forecast before that hour and no quality flag is present.  Any
    incomplete or invalid hour is excluded for every provider, preventing a
    source from receiving a score on an easier subset of observations.
    """
    plant = _name(plant_key, "plant_key")
    grouped: dict[datetime, dict[str, AsIssuedProviderPair]] = defaultdict(dict)
    providers: set[str] = set()
    for pair in pairs:
        if _name(pair.plant_key, "pair.plant_key") != plant:
            raise ValueError("pairs must belong to exactly one plant")
        provider = _name(pair.provider, "pair.provider")
        issued = _utc(pair.issued_at_utc, "pair.issued_at_utc")
        target = _hour_start(pair.target_at_utc, "pair.target_at_utc")
        if provider in grouped[target]:
            raise ValueError("each provider may appear once per target hour")
        # Retain normalized timestamps for deterministic comparison below.
        grouped[target][provider] = AsIssuedProviderPair(
            plant, provider, issued, target, pair.actual_kw, pair.predicted_kw,
            pair.daylight, tuple(pair.quality_flags),
        )
        providers.add(provider)
    if len(providers) < 2:
        raise ValueError("at least two providers are required for an ensemble scorecard")

    exclusions: Counter[str] = Counter()
    observations: list[ProviderObservation] = []
    eligible_hours = 0
    for target in sorted(grouped):
        by_provider = grouped[target]
        if set(by_provider) != providers:
            exclusions["incomplete_provider_coverage"] += 1
            continue
        if any(pair.issued_at_utc >= target for pair in by_provider.values()):
            exclusions["forecast_not_as_issued"] += 1
            continue
        if any(not pair.daylight for pair in by_provider.values()):
            exclusions["not_daylight"] += 1
            continue
        if any(pair.quality_flags for pair in by_provider.values()):
            exclusions["quality_flagged"] += 1
            continue
        eligible_hours += 1
        observations.extend(
            ProviderObservation(plant, provider, pair.actual_kw, pair.predicted_kw)
            for provider, pair in sorted(by_provider.items())
        )
    if not observations:
        raise ValueError("no comparable as-issued daylight hours are eligible")
    return AsIssuedScorecard(
        profile=calibrate(plant_key=plant, rated_ac_kw=rated_ac_kw,
                          observations=tuple(observations)),
        candidate_hours=len(grouped), eligible_hours=eligible_hours,
        excluded_hours=tuple(sorted(exclusions.items())),
    )
