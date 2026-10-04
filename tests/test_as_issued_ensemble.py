from datetime import datetime, timezone

import pytest

from app.as_issued_ensemble import AsIssuedProviderPair, score_as_issued


HOUR = datetime(2026, 10, 1, 10, tzinfo=timezone.utc)


def pair(provider, actual, predicted, *, target=HOUR, issued_hour=9,
         daylight=True, quality_flags=()):
    return AsIssuedProviderPair(
        "pohreby", provider,
        datetime(2026, 10, 1, issued_hour, tzinfo=timezone.utc), target,
        actual, predicted, daylight, quality_flags,
    )


def test_scores_only_complete_daylight_as_issued_hours_for_all_providers():
    later = datetime(2026, 10, 1, 11, tzinfo=timezone.utc)
    result = score_as_issued(plant_key="pohreby", rated_ac_kw=30, pairs=(
        pair("google_weather", 10, 9), pair("solcast", 10, 8),
        pair("google_weather", 8, 7, target=later, issued_hour=10, daylight=False),
        pair("solcast", 8, 9, target=later, issued_hour=10, daylight=False),
    ))
    assert result.candidate_hours == 2
    assert result.eligible_hours == 1
    assert result.excluded_hours == (("not_daylight", 1),)
    assert {score.provider: score.pair_count for score in result.profile.scores} == {
        "google_weather": 1, "solcast": 1,
    }


def test_excludes_entire_hour_for_missing_late_or_flagged_candidate():
    later = datetime(2026, 10, 1, 11, tzinfo=timezone.utc)
    flagged = datetime(2026, 10, 1, 12, tzinfo=timezone.utc)
    result = score_as_issued(plant_key="pohreby", rated_ac_kw=30, pairs=(
        pair("google_weather", 10, 9), pair("solcast", 10, 8),
        pair("google_weather", 9, 8, target=later, issued_hour=11),
        pair("solcast", 9, 7, target=later, issued_hour=10),
        pair("google_weather", 8, 8, target=flagged, issued_hour=11),
        pair("solcast", 8, 7, target=flagged, issued_hour=11, quality_flags=("outage",)),
    ))
    assert result.eligible_hours == 1
    assert dict(result.excluded_hours) == {
        "forecast_not_as_issued": 1,
        "quality_flagged": 1,
    }


def test_rejects_non_hourly_timestamps_duplicates_and_no_eligible_evidence():
    with pytest.raises(ValueError, match="hourly UTC boundary"):
        score_as_issued(plant_key="pohreby", rated_ac_kw=30, pairs=(
            pair("google_weather", 1, 1, target=HOUR.replace(minute=30)),
            pair("solcast", 1, 1, target=HOUR.replace(minute=30)),
        ))
    with pytest.raises(ValueError, match="once per target hour"):
        score_as_issued(plant_key="pohreby", rated_ac_kw=30, pairs=(
            pair("google_weather", 1, 1), pair("google_weather", 1, 1),
            pair("solcast", 1, 1),
        ))
    with pytest.raises(ValueError, match="no comparable"):
        score_as_issued(plant_key="pohreby", rated_ac_kw=30, pairs=(
            pair("google_weather", 1, 1, daylight=False),
            pair("solcast", 1, 1, daylight=False),
        ))
