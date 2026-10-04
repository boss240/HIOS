import json
from uuid import uuid4
import pytest
from app.deye_device_capture_job import parse_scope,run_job


def environment():
    return {'HIOS_DEYE_CAPTURE_SCOPE':json.dumps([
        {'plantId':'a','bindingId':str(uuid4()),'deviceSerial':'private-device'},
        {'plantId':'b','bindingId':str(uuid4()),'deviceSerial':'private-device-b'}]),
        'HIOS_DEYE_CAPTURE_START_UTC':'2020-01-01','HIOS_DEYE_CAPTURE_END_UTC':'2020-01-02',
        'DATABASE_URL':'private-db','HIOS_CAPTURE_SUBJECT':'operator','HIOS_CAPTURE_TENANT':'tenant'}


def test_job_passes_exact_scope_and_redacts_native_selection():
    calls=[]
    def collector(db,subject,**kwargs):
        calls.append((db,subject,kwargs));return ({'dayUtc':'2020-01-01','status':'stored'},)
    result=run_job(environment(),collector=collector,client_factory=lambda:object())
    assert len(calls)==2 and calls[0][2]['plant_id']=='a' and calls[1][2]['plant_id']=='b'
    assert 'private' not in repr(result) and result[1]['plantIndex']==1


def test_failed_first_plant_stops_second_without_disclosing_exception():
    calls=[]
    def collector(*args,**kwargs):
        calls.append(1);raise RuntimeError('private-secret')
    result=run_job(environment(),collector=collector,client_factory=lambda:object())
    assert len(calls)==1 and result[0]['status']=='failed' and 'private' not in repr(result)


def test_failed_day_stops_other_plant():
    calls=[]
    def collector(*args,**kwargs):
        calls.append(1);return ({'dayUtc':'2020-01-01','status':'failed','errorClass':'ValueError'},)
    assert len(run_job(environment(),collector=collector,client_factory=lambda:object()))==1
    assert len(calls)==1


@pytest.mark.parametrize('scope',[[],[{}], [{'plantId':'a','bindingId':'bad','deviceSerial':'x'}]])
def test_invalid_selection_rejected(scope):
    with pytest.raises((ValueError,TypeError)):parse_scope(json.dumps(scope))


def test_duplicate_plant_rejected_before_client_creation():
    env=environment();rows=json.loads(env['HIOS_DEYE_CAPTURE_SCOPE']);rows[1]['plantId']='a'
    env['HIOS_DEYE_CAPTURE_SCOPE']=json.dumps(rows)
    with pytest.raises(ValueError):run_job(env,client_factory=lambda:pytest.fail('provider created'))
