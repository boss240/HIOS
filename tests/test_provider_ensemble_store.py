from datetime import datetime, timezone

import pytest

from app.provider_ensemble import ProviderObservation, calibrate
from app.provider_ensemble_store import load_profile, replace_profile

pytest_plugins = ["test_runtime"]


def profile(plant_key="002"):
    return calibrate(plant_key=plant_key, rated_ac_kw=30, observations=(
        ProviderObservation(plant_key, "google_weather", 10, 9),
        ProviderObservation(plant_key, "google_weather", 20, 21),
        ProviderObservation(plant_key, "solcast", 10, 7),
        ProviderObservation(plant_key, "solcast", 20, 24),
    ))


def test_replaces_and_loads_a_tenant_owned_profile(db):
    now = datetime(2026, 9, 15, tzinfo=timezone.utc)
    replace_profile(database_url=db, subject="alice", tenant_id="a", profile=profile(), calibrated_at_utc=now)
    scores = load_profile(database_url=db, subject="alice", tenant_id="a", plant_id="002")
    assert [score.provider for score in scores] == ["google_weather", "solcast"]
    assert all(score.calibrated_at_utc == now for score in scores)
    assert sum(score.weight for score in scores) == pytest.approx(1)


def test_profile_store_rejects_other_tenant_and_naive_time(db):
    with pytest.raises(PermissionError):
        replace_profile(database_url=db, subject="bob", tenant_id="a", profile=profile(),
                        calibrated_at_utc=datetime(2026, 9, 15, tzinfo=timezone.utc))
    with pytest.raises(ValueError, match="timezone"):
        replace_profile(database_url=db, subject="alice", tenant_id="a", profile=profile(),
                        calibrated_at_utc=datetime(2026, 9, 15))
