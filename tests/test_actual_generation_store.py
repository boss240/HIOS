from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.actual_generation_store import ActualGenerationObservation, ActualGenerationSnapshot


def observation(**changes) -> ActualGenerationObservation:
    start = datetime(2026, 9, 9, 10, tzinfo=timezone.utc)
    values = {
        "provider": "deye_cloud",
        "mapping_version": "deye-actuals-v1",
        "observed_at_utc": start,
        "interval_end_utc": start + timedelta(hours=1),
        "retrieved_at_utc": start + timedelta(hours=2),
        "ac_power_kw": 12.5,
        "energy_kwh": 12.5,
        "quality_flags": ("source_verified",),
    }
    values.update(changes)
    return ActualGenerationObservation(**values)


def test_observation_requires_utc_interval_and_measured_value():
    assert observation().ac_power_kw == 12.5
    with pytest.raises(ValueError, match="at least one measured"):
        observation(ac_power_kw=None, energy_kwh=None)
    with pytest.raises(ValueError, match="retrieved_at_utc"):
        observation(retrieved_at_utc=datetime(2026, 9, 9, 9, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="finite non-negative"):
        observation(ac_power_kw=-1)


def test_snapshot_rejects_invalid_provenance_hash():
    with pytest.raises(ValueError, match="SHA-256"):
        ActualGenerationSnapshot(
            uuid4(), "tenant-a", "plant-a", "source-1", "not-a-hash", observation()
        )
