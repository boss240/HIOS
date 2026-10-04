from datetime import date,datetime,timezone
import pytest
from app.deye_device_collection import collect_device_days


class Client:
    def __init__(self):self.auth=0;self.days=[]
    def obtain_token(self):self.auth+=1;return 'private-token'
    def device_solar_history_for_day(self,token,serial,*,closed_day_utc):
        self.days.append(closed_day_utc);return {'deviceSn':serial}


def collect(client,**kwargs):
    return collect_device_days(client,device_serial='private-device',start_day=date(2026,10,1),
        end_day=date(2026,10,3),now=datetime(2026,10,4,tzinfo=timezone.utc),**kwargs)


def test_saved_days_require_no_authentication_or_provider_requests():
    client=Client()
    rows=collect(client,existing_capture=lambda day:True,persist_capture=lambda *args:pytest.fail())
    assert len(rows)==3 and all(r['status']=='already_stored' for r in rows)
    assert client.auth==0 and not client.days


def test_one_token_only_missing_days_and_exact_persistence():
    client=Client();saved=[]
    rows=collect(client,existing_capture=lambda day:day.day==2,
        persist_capture=lambda day,body:saved.append((day,body)))
    assert client.auth==1 and [d.day for d in client.days]==[1,3]
    assert [r['status'] for r in rows]==['stored','already_stored','stored']
    assert [d.day for d,_ in saved]==[1,3]
    assert 'private' not in repr(rows)


def test_auth_failure_stops_without_retry_or_disclosing_message():
    client=Client()
    def fail():client.auth+=1;raise RuntimeError('private-password')
    client.obtain_token=fail
    rows=collect(client,existing_capture=lambda day:False,persist_capture=lambda *args:pytest.fail())
    assert client.auth==1 and client.days==[] and len(rows)==1
    assert rows[0]['status']=='failed' and 'private' not in repr(rows)


def test_store_failure_preserves_prior_success_and_stops_further_reads():
    client=Client()
    def persist(day,body):
        if day.day==2:raise ValueError('invalid data')
    rows=collect(client,existing_capture=lambda day:False,persist_capture=persist)
    assert [r['status'] for r in rows]==['stored','failed']
    assert [d.day for d in client.days]==[1,2]


@pytest.mark.parametrize('start,end',[ (date(2026,10,3),date(2026,10,4)),
    (date(2026,8,1),date(2026,10,3)),(date(2026,10,3),date(2026,10,1))])
def test_invalid_window_rejected_before_requests(start,end):
    client=Client()
    with pytest.raises(ValueError):
        collect_device_days(client,device_serial='private',start_day=start,end_day=end,
            existing_capture=lambda day:False,persist_capture=lambda *args:None,
            now=datetime(2026,10,4,tzinfo=timezone.utc))
    assert client.auth==0
