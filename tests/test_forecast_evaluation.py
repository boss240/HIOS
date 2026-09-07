import pytest

from app.forecast_evaluation import EvaluationSample, evaluate


def test_calculates_documented_power_metrics():
    result = evaluate((
        EvaluationSample(100, 110, True), EvaluationSample(50, 40, True),
        EvaluationSample(0, 5, False),
    ), rated_ac_kw=200)

    assert result.pair_count == 3 and result.mape_pair_count == 2
    assert result.mae_kw == pytest.approx(25 / 3)
    assert result.rmse_kw == pytest.approx((225 / 3) ** 0.5)
    assert result.bias_kw == pytest.approx(5 / 3)
    assert result.mape_pct == pytest.approx(15)
    assert result.nmae_pct == pytest.approx(100 * (25 / 3) / 200)


def test_zero_pairs_are_not_evaluated_and_low_output_is_excluded_from_mape():
    empty = evaluate((), rated_ac_kw=100)
    assert empty.pair_count == 0 and empty.mae_kw is None and empty.mape_pct is None
    low = evaluate((EvaluationSample(1, 2, True),), rated_ac_kw=100)
    assert low.mape_pair_count == 0 and low.mape_pct is None


def test_rejects_invalid_power_values_and_capacity():
    with pytest.raises(ValueError):
        evaluate((EvaluationSample(-1, 0, True),), 100)
    with pytest.raises(ValueError):
        evaluate((EvaluationSample(1, float("nan"), True),), 100)
    with pytest.raises(ValueError):
        evaluate((), 0)
