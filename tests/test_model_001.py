import pytest

from app.model_001 import Model001Config, Model001Input, predict


@pytest.fixture
def config():
    return Model001Config(
        model_version="0.1.0-candidate", dc_capacity_kw=100, ac_capacity_kw=80,
        performance_ratio=0.8, temperature_coefficient_per_c=-0.004,
    )


def test_model_001_calculates_bounded_ac_power(config):
    result = predict(config, Model001Input(plane_of_array_irradiance_wm2=500, cell_temperature_c=25,
                                            solar_elevation_degrees=30))

    assert result.predicted_power_kw == 40
    assert result.quality_flags == ()


def test_model_001_clips_to_separate_ac_capacity(config):
    result = predict(config, Model001Input(plane_of_array_irradiance_wm2=1300, cell_temperature_c=25,
                                            solar_elevation_degrees=45))

    assert result.predicted_power_kw == 80
    assert result.quality_flags == ("ac_clipped",)


def test_model_001_outputs_zero_only_for_validated_night_context(config):
    result = predict(config, Model001Input(plane_of_array_irradiance_wm2=700, cell_temperature_c=25,
                                            solar_elevation_degrees=0))

    assert result.predicted_power_kw == 0
    assert result.quality_flags == ("solar_night",)


@pytest.mark.parametrize("features", [
    Model001Input(plane_of_array_irradiance_wm2=-1, cell_temperature_c=25, solar_elevation_degrees=20),
    Model001Input(plane_of_array_irradiance_wm2=1, cell_temperature_c=float("nan"), solar_elevation_degrees=20),
])
def test_model_001_rejects_missing_or_invalid_features(config, features):
    with pytest.raises(ValueError):
        predict(config, features)


def test_model_001_requires_positive_separate_capacity_and_nonpositive_temperature_coefficient():
    with pytest.raises(ValueError, match="dc_capacity"):
        Model001Config("candidate", 0, 10, 0.8, -0.004)
    with pytest.raises(ValueError, match="must not be positive"):
        Model001Config("candidate", 10, 10, 0.8, 0.004)
