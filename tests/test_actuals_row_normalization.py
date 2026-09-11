from datetime import datetime, timedelta, timezone

import pytest

from app.actuals_field_mapping import ActualsFieldMapping, EnergySemantics
from app.actuals_row_normalization import normalize_actuals_row


START = datetime(2026, 9, 11, 10, tzinfo=timezone.utc)


def mapping(**changes) -> ActualsFieldMapping:
    values = {
        "provider": "approved_provider", "mapping_version": "approved-v1",
        "source_timezone": "Europe/Kyiv", "observed_at_field": "observed",
        "interval_end_field": "intervalEnd", "power_field": "power", "power_unit": "W",
        "energy_field": "energy", "energy_unit": "Wh",
        "energy_semantics": EnergySemantics.INTERVAL, "status_field": "status",
    }
    values.update(changes)
    return ActualsFieldMapping(**values)


def test_normalizes_only_mapped_fields_into_an_unstored_observation():
    observation = normalize_actuals_row(
        mapping=mapping(),
        row={"observed": "provider-time", "intervalEnd": "provider-end", "power": 12_500,
             "energy": 6_250, "status": "online", "ignored": "not retained"},
        observed_at_utc=START, interval_end_utc=START + timedelta(minutes=30),
        retrieved_at_utc=START + timedelta(minutes=31), quality_flags=("source_verified",),
    )

    assert observation.ac_power_kw == 12.5
    assert observation.energy_kwh == 6.25
    assert observation.energy_semantics is EnergySemantics.INTERVAL
    assert observation.device_status == "online"
    assert observation.quality_flags == ("source_verified",)


def test_rejects_schema_drift_and_invalid_mapped_values():
    base = {"observed": "x", "intervalEnd": "y", "power": 1, "energy": 1, "status": "online"}
    kwargs = {"mapping": mapping(), "observed_at_utc": START,
              "interval_end_utc": START + timedelta(minutes=1), "retrieved_at_utc": START}
    with pytest.raises(ValueError, match="mapped energy"):
        normalize_actuals_row(row={key: value for key, value in base.items() if key != "energy"}, **kwargs)
    with pytest.raises(ValueError, match="finite non-negative"):
        normalize_actuals_row(row={**base, "power": -1}, **kwargs)
    with pytest.raises(ValueError, match="status field"):
        normalize_actuals_row(row={**base, "status": 1}, **kwargs)
