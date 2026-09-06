"""Deterministic MODEL-001 candidate with explicit physical bounds.

This is an untrained candidate, not a calibrated production model.  It consumes
plane-of-array irradiance supplied by a separately versioned feature pipeline;
GHI must never be passed here as an undocumented substitute.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


def _finite(value: float, name: str, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return result


@dataclass(frozen=True)
class Model001Config:
    model_version: str
    dc_capacity_kw: float
    ac_capacity_kw: float
    performance_ratio: float
    temperature_coefficient_per_c: float
    reference_cell_temperature_c: float = 25.0

    def __post_init__(self) -> None:
        if not self.model_version.strip():
            raise ValueError("model_version must be non-empty")
        _finite(self.dc_capacity_kw, "dc_capacity_kw", 0.000001)
        _finite(self.ac_capacity_kw, "ac_capacity_kw", 0.000001)
        ratio = _finite(self.performance_ratio, "performance_ratio", 0)
        if ratio > 1:
            raise ValueError("performance_ratio must be at most 1")
        coefficient = _finite(self.temperature_coefficient_per_c, "temperature_coefficient_per_c")
        if coefficient > 0:
            raise ValueError("temperature_coefficient_per_c must not be positive")
        _finite(self.reference_cell_temperature_c, "reference_cell_temperature_c")


@dataclass(frozen=True)
class Model001Input:
    plane_of_array_irradiance_wm2: float
    cell_temperature_c: float
    solar_elevation_degrees: float


@dataclass(frozen=True)
class Model001Output:
    predicted_power_kw: float
    quality_flags: tuple[str, ...]


def predict(config: Model001Config, features: Model001Input) -> Model001Output:
    """Calculate bounded AC power from ready, versioned model features."""
    poa = _finite(features.plane_of_array_irradiance_wm2, "plane_of_array_irradiance_wm2", 0)
    cell_temperature = _finite(features.cell_temperature_c, "cell_temperature_c")
    elevation = _finite(features.solar_elevation_degrees, "solar_elevation_degrees")
    if elevation <= 0:
        return Model001Output(predicted_power_kw=0.0, quality_flags=("solar_night",))
    temperature_factor = 1 + config.temperature_coefficient_per_c * (
        cell_temperature - config.reference_cell_temperature_c
    )
    unconstrained_dc_kw = config.dc_capacity_kw * (poa / 1000) * config.performance_ratio * temperature_factor
    predicted = min(config.ac_capacity_kw, max(0.0, unconstrained_dc_kw))
    flags = ("ac_clipped",) if unconstrained_dc_kw > config.ac_capacity_kw else ()
    return Model001Output(predicted_power_kw=predicted, quality_flags=flags)
