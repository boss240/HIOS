from datetime import datetime, timezone
import pytest
from app.evaluation_policy import EvaluationPolicy, register_policy
pytest_plugins=['test_runtime']

def policy(**changes):
    values=dict(tenant_id='a',plant_id='002',policy_version='holdout-v1',max_mae_kw=2.5,max_nmae_percent=10,max_daylight_mape_percent=25,min_eligible_pairs=168,approved_by='forecast-owner',approved_at_utc=datetime(2026,9,15,tzinfo=timezone.utc));values.update(changes);return EvaluationPolicy(**values)

def test_registers_policy_once_with_tenant_ownership(db):
    assert register_policy(db,'alice',policy()) is True
    assert register_policy(db,'alice',policy()) is False
    with pytest.raises(PermissionError): register_policy(db,'bob',policy())

def test_rejects_unspecified_or_naive_threshold_policy():
    with pytest.raises(ValueError,match='UTC'): policy(approved_at_utc=datetime(2026,9,15))
    with pytest.raises(ValueError,match='max_mae_kw'): policy(max_mae_kw=0)