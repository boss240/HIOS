"""Versioned field and unit mapping contract for read-only generation actuals."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class EnergySemantics(str, Enum):
    INTERVAL = "interval"
    CUMULATIVE = "cumulative"


def _name(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _value(value: float | None, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite non-negative number when supplied")
    return float(value)


@dataclass(frozen=True)
class ActualsFieldMapping:
    provider: str
    mapping_version: str
    source_timezone: str
    observed_at_field: str
    interval_end_field: str
    power_field: str | None = None
    power_unit: str | None = None
    energy_field: str | None = None
    energy_unit: str | None = None
    energy_semantics: EnergySemantics | None = None
    status_field: str | None = None

    def __post_init__(self) -> None:
        for name in ("provider", "mapping_version", "observed_at_field", "interval_end_field"):
            _name(getattr(self, name), name)
        try:
            ZoneInfo(_name(self.source_timezone, "source_timezone"))
        except ZoneInfoNotFoundError as error:
            raise ValueError("source_timezone must be an IANA timezone") from error
        self._validate_measurement("power", {"W", "kW"}, None)
        self._validate_measurement("energy", {"Wh", "kWh"}, EnergySemantics)
        if self.power_field is None and self.energy_field is None:
            raise ValueError("at least one mapped measurement field is required")
        if self.status_field is not None:
            _name(self.status_field, "status_field")

    def _validate_measurement(self, prefix: str, units: set[str], semantics_type: type[EnergySemantics] | None) -> None:
        field = getattr(self, f"{prefix}_field")
        unit = getattr(self, f"{prefix}_unit")
        semantics = getattr(self, f"{prefix}_semantics", None)
        if field is None:
            if unit is not None or semantics is not None:
                raise ValueError(f"{prefix}_unit and semantics require a {prefix}_field")
            return
        _name(field, f"{prefix}_field")
        if unit not in units:
            raise ValueError(f"{prefix}_unit must be one of {', '.join(sorted(units))}")
        if semantics_type is not None and not isinstance(semantics, semantics_type):
            raise ValueError("energy_semantics is required when energy_field is mapped")


@dataclass(frozen=True)
class CanonicalActualMeasurements:
    ac_power_kw: float | None
    energy_kwh: float | None
    energy_semantics: EnergySemantics | None


def canonicalize_measurements(mapping: ActualsFieldMapping, *, raw_power: float | None,
                              raw_energy: float | None) -> CanonicalActualMeasurements:
    """Convert a mapped provider value to canonical kW/kWh without calling a provider."""
    if mapping.power_field is None and raw_power is not None:
        raise ValueError("raw_power is present without a mapped power_field")
    if mapping.energy_field is None and raw_energy is not None:
        raise ValueError("raw_energy is present without a mapped energy_field")
    power = _value(raw_power, "raw_power")
    energy = _value(raw_energy, "raw_energy")
    if power is not None and mapping.power_unit == "W":
        power /= 1000
    if energy is not None and mapping.energy_unit == "Wh":
        energy /= 1000
    if power is None and energy is None:
        raise ValueError("at least one mapped measurement value is required")
    return CanonicalActualMeasurements(power, energy, mapping.energy_semantics if energy is not None else None)
