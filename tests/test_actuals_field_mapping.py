import pytest

from app.actuals_field_mapping import (
    ActualsFieldMapping,
    EnergySemantics,
    canonicalize_measurements,
)


def mapping(**changes) -> ActualsFieldMapping:
    values = {
        "provider": "deye_cloud",
        "mapping_version": "deye-actuals-v1",
        "source_timezone": "Europe/Kyiv",
        "observed_at_field": "timestamp",
        "interval_end_field": "intervalEnd",
        "power_field": "acPower",
        "power_unit": "W",
        "energy_field": "intervalEnergy",
        "energy_unit": "Wh",
        "energy_semantics": EnergySemantics.INTERVAL,
        "status_field": "status",
    }
    values.update(changes)
    return ActualsFieldMapping(**values)


def test_mapping_requires_units_and_energy_semantics():
    assert mapping().source_timezone == "Europe/Kyiv"
    with pytest.raises(ValueError, match="energy_semantics"):
        mapping(energy_semantics=None)
    with pytest.raises(ValueError, match="IANA timezone"):
        mapping(source_timezone="Kyiv")
    with pytest.raises(ValueError, match="at least one mapped"):
        mapping(power_field=None, power_unit=None, energy_field=None,
                energy_unit=None, energy_semantics=None)


def test_canonicalizes_units_without_losing_energy_semantics():
    result = canonicalize_measurements(mapping(), raw_power=12500, raw_energy=25000)

    assert result.ac_power_kw == 12.5
    assert result.energy_kwh == 25
    assert result.energy_semantics is EnergySemantics.INTERVAL
    with pytest.raises(ValueError, match="without a mapped power_field"):
        canonicalize_measurements(
            mapping(power_field=None, power_unit=None), raw_power=1, raw_energy=1
        )
