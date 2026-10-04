"""Chronological held-out evidence for a fixed per-plant forecast blend."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime,timedelta,timezone
from app.as_issued_ensemble import AsIssuedProviderPair,score_as_issued
from app.provider_ensemble import mix_hour


@dataclass(frozen=True)
class RecordedPair:
    pair: AsIssuedProviderPair
    actual_available_at_utc: datetime


def utc(value):
    if not isinstance(value,datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('aware evidence timestamps required')
    return value.astimezone(timezone.utc)


def evaluate_holdout(*,plant_key,rated_ac_kw,training,holdout,training_cutoff_utc,
                     analysis_as_of_utc,baseline_provider,min_training_hours=24,min_holdout_hours=24):
    """Fit only earlier available facts; compare a frozen blend on later hours.

    Caller must establish common AC measurement scope and immutable source
    lineage. This pure helper neither publishes a model nor grants a licence.
    Minimum hour counts are evaluation policy, not an accuracy guarantee.
    """
    cutoff=utc(training_cutoff_utc);as_of=utc(analysis_as_of_utc)
    if cutoff>=as_of:raise ValueError('analysis must follow training cutoff')
    for value in (min_training_hours,min_holdout_hours):
        if isinstance(value,bool) or not isinstance(value,int) or value<2:
            raise ValueError('minimum evidence counts must be at least two')
    training=tuple(training);holdout=tuple(holdout)
    for rows,is_training in ((training,True),(holdout,False)):
        for record in rows:
            end=utc(record.pair.target_at_utc)+timedelta(hours=1)
            receipt=utc(record.actual_available_at_utc)
            if receipt<end:raise ValueError('actual evidence cannot precede closed target hour')
            if is_training:
                if end>cutoff or receipt>cutoff:raise ValueError('training facts were unavailable at cutoff')
            elif utc(record.pair.forecast_origin_utc)<cutoff or end>as_of or receipt>as_of:
                raise ValueError('holdout must follow cutoff and be available at analysis')
    fit=score_as_issued(plant_key=plant_key,rated_ac_kw=rated_ac_kw,pairs=(r.pair for r in training))
    providers=set(fit.profile.weights())
    if baseline_provider not in providers:raise ValueError('baseline must be a trained provider')
    if {r.pair.provider.strip() for r in holdout}!=providers:
        raise ValueError('holdout provider set must match training')
    # Validate all rows before filtering incomplete or flagged hours.
    checked=score_as_issued(plant_key=plant_key,rated_ac_kw=rated_ac_kw,pairs=(r.pair for r in holdout))
    grouped=defaultdict(list)
    for record in holdout:grouped[utc(record.pair.target_at_utc)].append(record.pair)
    errors=[]
    for target,rows in sorted(grouped.items()):
        if {r.provider.strip() for r in rows}!=providers:continue
        try:score_as_issued(plant_key=plant_key,rated_ac_kw=rated_ac_kw,pairs=rows)
        except ValueError:continue  # full validation above already rejected malformed inputs
        actual=rows[0].actual_kw
        predictions={r.provider.strip():r.predicted_kw for r in rows}
        errors.append((mix_hour(profile=fit.profile,predictions_kw=predictions)-actual,
                       predictions[baseline_provider]-actual))
    if fit.eligible_hours<min_training_hours or len(errors)<min_holdout_hours:
        raise ValueError('insufficient training or held-out evidence')
    blend_mae=sum(abs(e[0]) for e in errors)/len(errors)
    baseline_mae=sum(abs(e[1]) for e in errors)/len(errors)
    return {'plantKey':plant_key,'trainingHours':fit.eligible_hours,'holdoutHours':len(errors),
        'holdoutCandidateHours':checked.candidate_hours,'holdoutExcludedHours':checked.excluded_hours,
        'trainingCutoffUtc':cutoff.isoformat(),'analysisAsOfUtc':as_of.isoformat(),
        'weights':fit.profile.weights(),'baselineProvider':baseline_provider,
        'blendMaeKw':blend_mae,'baselineMaeKw':baseline_mae,
        'blendBiasKw':sum(e[0] for e in errors)/len(errors),
        'baselineBiasKw':sum(e[1] for e in errors)/len(errors),
        'maeImprovementPct':None if baseline_mae==0 else 100*(baseline_mae-blend_mae)/baseline_mae,
        'publication':'not_approved','licenceEligibility':'not_assessed'}
