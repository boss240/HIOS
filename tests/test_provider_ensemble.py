import pytest

from app.provider_ensemble import ProviderObservation, calibrate, mix_hour


def observations():
    return (
        ProviderObservation("pohreby", "google_weather", 10, 9),
        ProviderObservation("pohreby", "google_weather", 20, 21),
        ProviderObservation("pohreby", "solcast", 10, 7),
        ProviderObservation("pohreby", "solcast", 20, 24),
    )


def test_scores_and_mixes_providers_per_plant():
    profile = calibrate(plant_key="pohreby", rated_ac_kw=30, observations=observations())
    scores = {score.provider: score for score in profile.scores}
    assert scores["google_weather"].mae_kw == pytest.approx(1)
    assert scores["solcast"].mae_kw == pytest.approx(3.5)
    assert scores["google_weather"].weight > scores["solcast"].weight
    assert sum(score.weight for score in profile.scores) == pytest.approx(1)
    assert mix_hour(profile=profile, predictions_kw={"google_weather": 15, "solcast": 20}) == pytest.approx(
        scores["google_weather"].weight * 15 + scores["solcast"].weight * 20
    )


def test_rejects_cross_plant_pairs_or_partial_hourly_coverage():
    with pytest.raises(ValueError, match="exactly one plant"):
        calibrate(plant_key="pohreby", rated_ac_kw=30, observations=(
            ProviderObservation("borshchiv", "google_weather", 10, 9),
        ))
    profile = calibrate(plant_key="pohreby", rated_ac_kw=30, observations=observations())
    with pytest.raises(ValueError, match="exactly the calibrated providers"):
        mix_hour(profile=profile, predictions_kw={"google_weather": 15})
