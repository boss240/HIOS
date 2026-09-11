from app.deye_frame_quality import audit_station_frame_history


def test_audits_expected_shape_without_mapping_any_field():
    result = audit_station_frame_history({"stationDataItems": [
        {"timeStamp": 1_789_084_800, "generationPower": 12_500, "generationValue": 8.5},
        {"timeStamp": 1_789_085_100, "generationPower": 12_400, "generationValue": 8.7},
    ]})

    assert result.sample_count == 2
    assert result.valid_timestamp_count == 2
    assert result.cadence_seconds == (300,)
    assert result.generation_power_numeric_count == 2
    assert result.generation_value_numeric_count == 2
    assert result.flags == ()


def test_flags_schema_and_quality_failures_without_returning_payload():
    result = audit_station_frame_history({"stationDataItems": [
        {"timeStamp": 1_789_085_100, "generationPower": -1, "generationValue": float("nan")},
        {"timeStamp": 1_789_084_800, "generationValue": 3},
        {"timeStamp": 1_789_085_700, "generationPower": 1, "generationValue": 3},
        {"timeStamp": 1_789_085_700, "generationPower": 1, "generationValue": 3},
    ]})

    assert result.sample_count == 4
    assert result.valid_timestamp_count == 4
    assert result.cadence_seconds == (300, 600)
    assert result.generation_power_numeric_count == 2
    assert result.generation_value_numeric_count == 3
    assert result.flags == (
        "cadence_irregular",
        "generationPower_missing",
        "generation_power_invalid",
        "generation_value_invalid",
        "timestamp_duplicate",
        "timestamp_not_monotonic",
    )


def test_missing_station_data_items_is_an_explicit_blocker():
    result = audit_station_frame_history({"data": []})

    assert result.sample_count == 0
    assert result.flags == ("station_data_items_missing",)
