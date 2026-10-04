from dataclasses import replace
from datetime import datetime,timedelta,timezone
import pytest
from app.as_issued_ensemble import AsIssuedProviderPair
from app.ensemble_holdout import RecordedPair,evaluate_holdout

CUTOFF=datetime(2026,10,2,tzinfo=timezone.utc)
def records(target,origin,baseline_error,challenger_error):
    return tuple(RecordedPair(AsIssuedProviderPair('plant',provider,origin,target,10,10+error,
        True,origin,origin),target+timedelta(hours=1)) for provider,error in
        [('baseline',baseline_error),('challenger',challenger_error)])
def evidence():
    train=records(CUTOFF-timedelta(hours=3),CUTOFF-timedelta(hours=5),4,0)+records(
        CUTOFF-timedelta(hours=2),CUTOFF-timedelta(hours=5),4,0)
    test=records(CUTOFF+timedelta(hours=1),CUTOFF,0,4)+records(CUTOFF+timedelta(hours=2),CUTOFF,0,4)
    return train,test
def evaluate(train,test,**changes):
    args=dict(plant_key='plant',rated_ac_kw=30,training=train,holdout=test,
        training_cutoff_utc=CUTOFF,analysis_as_of_utc=CUTOFF+timedelta(hours=4),
        baseline_provider='baseline',min_training_hours=2,min_holdout_hours=2)
    return evaluate_holdout(**(args|changes))
def test_holdout_does_not_refit_weights_to_better_later_baseline():
    train,test=evidence();result=evaluate(train,test)
    assert result['weights']['challenger']>result['weights']['baseline']
    assert result['blendMaeKw']>3 and result['baselineMaeKw']==0
    assert result['maeImprovementPct'] is None
    assert result['publication']=='not_approved' and result['licenceEligibility']=='not_assessed'
def test_training_facts_received_after_cutoff_are_rejected():
    train,test=evidence();late=replace(train[0],actual_available_at_utc=CUTOFF+timedelta(seconds=1))
    with pytest.raises(ValueError,match='unavailable'):evaluate((late,)+train[1:],test)
def test_test_forecast_origin_before_training_cutoff_is_rejected():
    train,test=evidence();late=replace(test[0],pair=replace(test[0].pair,forecast_origin_utc=CUTOFF-timedelta(hours=1)))
    with pytest.raises(ValueError,match='holdout'):evaluate(train,(late,)+test[1:])
def test_actuals_not_yet_available_at_analysis_are_rejected():
    train,test=evidence();late=replace(test[0],actual_available_at_utc=CUTOFF+timedelta(days=1))
    with pytest.raises(ValueError,match='holdout'):evaluate(train,(late,)+test[1:])
def test_insufficient_evidence_does_not_report_accuracy():
    train,test=evidence()
    with pytest.raises(ValueError,match='insufficient'):evaluate(train,test,min_holdout_hours=3)
def test_heldout_deterioration_is_reported_as_negative_improvement():
    train,test=evidence();test=tuple(replace(r,pair=replace(r.pair,predicted_kw=11 if r.pair.provider=='baseline' else 14)) for r in test)
    assert evaluate(train,test)['maeImprovementPct']<0
def test_cross_plant_evidence_is_rejected():
    train,test=evidence();bad=replace(test[0],pair=replace(test[0].pair,plant_key='foreign'))
    with pytest.raises(ValueError,match='one plant'):evaluate(train,(bad,)+test[1:])
