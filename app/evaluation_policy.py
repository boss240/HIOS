"""Immutable tenant-safe acceptance thresholds for forecast holdout evaluation."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import math
import psycopg

@dataclass(frozen=True)
class EvaluationPolicy:
    tenant_id: str; plant_id: str; policy_version: str; max_mae_kw: float; max_nmae_percent: float
    max_daylight_mape_percent: float; min_eligible_pairs: int; approved_by: str; approved_at_utc: datetime
    def __post_init__(self):
        if not all(isinstance(v,str) and v.strip() for v in (self.tenant_id,self.plant_id,self.policy_version,self.approved_by)): raise ValueError('policy identifiers must be non-empty')
        if self.approved_at_utc.tzinfo is None or self.approved_at_utc.utcoffset() is None or self.approved_at_utc.astimezone(timezone.utc)!=self.approved_at_utc: raise ValueError('approved_at_utc must be UTC')
        if not isinstance(self.min_eligible_pairs,int) or isinstance(self.min_eligible_pairs,bool) or self.min_eligible_pairs<=0: raise ValueError('min_eligible_pairs must be positive')
        for value,name in ((self.max_mae_kw,'max_mae_kw'),(self.max_nmae_percent,'max_nmae_percent'),(self.max_daylight_mape_percent,'max_daylight_mape_percent')):
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0: raise ValueError(f'{name} must be positive and finite')

def register_policy(database_url: str, subject: str, policy: EvaluationPolicy) -> bool:
    with psycopg.connect(database_url,connect_timeout=5) as c:
        row=c.execute('''WITH owned AS (SELECT 1 FROM plant p JOIN membership m ON m.tenant_id=p.tenant_id WHERE p.tenant_id=%s AND p.public_id=%s AND m.subject=%s AND m.active), inserted AS (INSERT INTO forecast_evaluation_policy(tenant_id,plant_id,policy_version,max_mae_kw,max_nmae_percent,max_daylight_mape_percent,min_eligible_pairs,approved_by,approved_at_utc) SELECT %s,%s,%s,%s,%s,%s,%s,%s,%s FROM owned ON CONFLICT DO NOTHING RETURNING 1) SELECT EXISTS(SELECT 1 FROM owned),EXISTS(SELECT 1 FROM inserted)''',(policy.tenant_id,policy.plant_id,subject,policy.tenant_id,policy.plant_id,policy.policy_version,policy.max_mae_kw,policy.max_nmae_percent,policy.max_daylight_mape_percent,policy.min_eligible_pairs,policy.approved_by,policy.approved_at_utc)).fetchone()
    if not row[0]: raise PermissionError('Active membership and tenant-owned plant are required')
    return row[1]