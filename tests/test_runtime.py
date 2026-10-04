import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import jwt
import psycopg
import pytest
import yaml
import app.main as main_module
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from app.main import create_app
from app.migrate import migrate
from app.forecast_store import ForecastPoint, ForecastRun, create_or_get_run, publish_points
from app.model_registry import ModelCandidate, register_candidate, resolve_approved_candidate
from app.forecast_job import ForecastWeatherInput, configuration_hash, execute_model_001, input_hash
from app.model_001 import Model001Config
from app.feature_assembly import PlantGeometry
from app.forecast_schedule import JobKey, ScheduleSpec, claim_lease, latest_due_origin, release_lease
from app.forecast_worker import run_once
from app.forecast_operations import summarize_outcomes
from app.weather_normalization import normalize_weather
from app.weather_store import WeatherSnapshot, create_or_get_snapshot
from app.provider_forecast_capture import store_forecast_capture
from app.weather_provider_response import ProviderWeatherInterval
from app.provider_forecast_collection import collect_provider_forecast, list_provider_captures
from app.plant_onboarding import update_plant_profile, get_onboarding
from app.weather_capture_job import run_capture_job
from app.actual_generation_store import (
    ActualGenerationObservation,
    ActualGenerationSnapshot,
    create_or_get_actual_snapshot,
)
from app.actuals_field_mapping import EnergySemantics
from app.actuals_alignment import load_aligned_power_samples

SPEC = yaml.safe_load(Path("docs/api/openapi.yaml").read_text())


def test_device_solar_capture_is_owned_idempotent_and_immutable(db):
    from datetime import date
    from app.deye_solar_capture_store import store_device_solar_capture
    body = {'deviceSn':'private', 'dataList':[
        {'time':'1577836800','itemList':[{'key':'TotalSolarPower','unit':'W','value':'1000'}]},
        {'time':'1577837100','itemList':[{'key':'TotalSolarPower','unit':'W','value':'1000'}]}]}
    options = dict(tenant_id='a',plant_id='002',device_serial='private',
                   day=date(2020,1,1),retrieved_at=datetime(2020,1,2,tzinfo=timezone.utc),body=body)
    first = store_device_solar_capture(db,'alice',**options)
    assert store_device_solar_capture(db,'alice',**options) == first
    with pytest.raises(PermissionError):
        store_device_solar_capture(db,'bob',**options)
    with pytest.raises(PermissionError):
        store_device_solar_capture(db,'alice',**{**options,'plant_id':'001'})
    with psycopg.connect(db) as connection:
        document = connection.execute('SELECT document FROM device_solar_capture').fetchone()[0]
        assert 'private' not in str(document)
        assert document['scope'] == 'device_only'
        from app.deye_solar_archive import list_device_solar_archive
        archive=list_device_solar_archive(db,'alice',tenant_id='a',plant_id='002',
                                         start_day=date(2020,1,1),end_day=date(2020,1,1))
        assert len(archive)==1 and archive[0]['sampleCount']==2
        assert 'private' not in str(archive)
        assert 'device_sha256' not in str(archive)
        with pytest.raises(PermissionError):
            list_device_solar_archive(db,'bob',tenant_id='a',plant_id='002',
                                     start_day=date(2020,1,1),end_day=date(2020,1,1))
        assert document['hours'][0]['coveredSeconds'] == 300
        assert not document['hours'][0]['complete']
        assert connection.execute('SELECT count(*) FROM actual_generation_snapshot').fetchone()[0] == 0
        with pytest.raises(psycopg.Error):
            connection.execute('UPDATE device_solar_capture SET document=document')


def test_weather_pv_analysis_pairs_owned_captures_and_denies_mixed_plants(db,keys,monkeypatch):
    from datetime import date
    from app.deye_solar_capture_store import store_device_solar_capture
    monkeypatch.setenv('HIOS_DASHBOARD_USER','operator')
    monkeypatch.setenv('HIOS_DASHBOARD_PASSWORD','test-only-password')
    auth=('operator','test-only-password')
    with TestClient(create_app(db,keys[1],'hios-test','hios-api')) as dashboard:
        plant=dashboard.post('/dashboard/plants',auth=auth,json={'name':'Alignment A'}).json()['data']['id']
        other=dashboard.post('/dashboard/plants',auth=auth,json={'name':'Alignment B'}).json()['data']['id']
        with psycopg.connect(db) as connection:
            tenant,subject=connection.execute('SELECT p.tenant_id,m.subject FROM plant p JOIN membership m ON m.tenant_id=p.tenant_id WHERE p.public_id=%s',(plant,)).fetchone()
        receipt=datetime(2020,1,1,9,tzinfo=timezone.utc)
        start=receipt+timedelta(hours=1)
        selected=[]
        for provider,values in [('google_weather',{'temperature_c':20,'cloud_cover_pct':10,'wind_speed_ms':2}),
                                ('solcast',{'irradiance_global_wm2':500,'irradiance_direct_wm2':400,'irradiance_diffuse_wm2':100})]:
            selected.append(str(store_forecast_capture(db,subject,capture_id=uuid4(),tenant_id=tenant,plant_id=plant,
                provider=provider,mapping_version='v1',captured_at=receipt,
                intervals=(ProviderWeatherInterval(provider,start,start+timedelta(hours=1),values),))))
        body={'deviceSn':'selected','dataList':[{'time':str(int(start.timestamp())+offset),
            'itemList':[{'key':'TotalSolarPower','unit':'W','value':'1000'}]} for offset in range(0,3601,300)]}
        def store(target):
            return str(store_device_solar_capture(db,subject,tenant_id=tenant,plant_id=target,
                device_serial='selected',day=date(2020,1,1),retrieved_at=datetime(2020,1,2,tzinfo=timezone.utc),body=body))
        solar,foreign=store(plant),store(other)
        request={'weatherCaptureIds':selected,'solarCaptureId':solar,'forecastOriginUtc':receipt.isoformat()}
        path='/dashboard/plants/'+plant+'/weather-pv-analysis'
        assert dashboard.post(path,json=request).status_code==401
        result=dashboard.post(path,json=request,auth=auth)
        assert result.status_code==200
        data=result.json()['data'];assert len(data['pairs'])==1
        assert data['pairs'][0]['derivedDevicePvEnergyKwh']==pytest.approx(1)
        assert data['generationAccuracy']=='not_evaluated' and data['solarCaptureId']==solar
        assert dashboard.post(path,json={**request,'solarCaptureId':foreign},auth=auth).status_code==403
        assert dashboard.post(path,json={**request,'weatherCaptureIds':[selected[0],selected[0]]},auth=auth).status_code==400
        assert dashboard.post(path,json={**request,'analysisAsOfUtc':'2099-01-01'},auth=auth).status_code==400
        with psycopg.connect(db) as connection:
            assert connection.execute('SELECT count(*) FROM actual_generation_snapshot').fetchone()[0]==0
            assert connection.execute('SELECT count(*) FROM forecast_run').fetchone()[0]==0


def test_solar_archive_http_requires_auth_owned_plant_and_bounded_dates(db,keys,monkeypatch):
    monkeypatch.setenv('HIOS_DASHBOARD_USER','operator')
    monkeypatch.setenv('HIOS_DASHBOARD_PASSWORD','test-only-password')
    auth=('operator','test-only-password')
    with TestClient(create_app(db,keys[1],'hios-test','hios-api')) as dashboard:
        plant=dashboard.post('/dashboard/plants',auth=auth,json={'name':'Archive test'}).json()['data']['id']
        path='/dashboard/plants/'+plant+'/solar-history'
        query={'start':'2020-01-01','end':'2020-01-31'}
        assert dashboard.get(path,params=query).status_code==401
        assert dashboard.get(path+'.xlsx',params=query).status_code==401
        excel=dashboard.get(path+'.xlsx',params=query,auth=auth)
        assert excel.status_code==200 and excel.content.startswith(b'PK')
        assert excel.headers['cache-control']=='no-store'
        assert dashboard.get('/dashboard/plants/001/solar-history.xlsx',params=query,auth=auth).status_code==403
        assert dashboard.get(path,params=query,auth=auth).json()=={'data':[]}
        assert dashboard.get('/dashboard/plants/001/solar-history',params=query,auth=auth).status_code==403
        assert dashboard.get(path,params={**query,'end':'2020-02-01'},auth=auth).status_code==400
        assert dashboard.get(path,params={**query,'start':'invalid'},auth=auth).status_code==400


def test_dc_capacity_patch_preserves_profile_and_checks_owner(db):
    with psycopg.connect(db) as connection:
        connection.execute("INSERT INTO plant_profile(plant_id,tilt_deg) VALUES ('002',30)")
    options=dict(database_url=db,tenant_id='a',plant_id='002',changes={'capacityKw':25})
    with pytest.raises(PermissionError):update_plant_profile(subject='bob',**options)
    update_plant_profile(subject='alice',**options)
    saved=get_onboarding(database_url=db,subject='alice',tenant_id='a',plant_id='002')
    assert saved['capacityKw']==25 and saved['tiltDeg']==30
    for invalid in (True,0,-1,float('nan'),'25'):
        with pytest.raises(ValueError):update_plant_profile(subject='alice',**{**options,'changes':{'capacityKw':invalid}})
    update_plant_profile(subject='alice',**{**options,'changes':{'capacityKw':None}})
    assert 'capacityKw' not in get_onboarding(database_url=db,subject='alice',tenant_id='a',plant_id='002')


def test_protected_candidate_preview_uses_owned_passport_and_writes_no_forecasts(db,keys,monkeypatch):
    monkeypatch.setenv('HIOS_DASHBOARD_USER','operator')
    monkeypatch.setenv('HIOS_DASHBOARD_PASSWORD','test-only-password')
    receipt=datetime(2026,1,1,8,tzinfo=timezone.utc)
    auth=('operator','test-only-password')
    with TestClient(create_app(db,keys[1],'hios-test','hios-api')) as dashboard:
        created=dashboard.post('/dashboard/plants',auth=auth,json={'name':'Explicit preview test',
            'capacityKw':30,'capacityAcKw':10,'latitude':50.54,'longitude':30.62,'tiltDeg':30,
            'azimuthDeg':180,'meterBoundary':'AC inverter output'})
        assert created.status_code==201
        plant=created.json()['data']['id']
        with psycopg.connect(db) as connection:
            tenant,subject=connection.execute('''SELECT p.tenant_id,m.subject FROM plant p
                JOIN membership m ON m.tenant_id=p.tenant_id WHERE p.public_id=%s''',(plant,)).fetchone()
            before=connection.execute('SELECT count(*) FROM forecast_run').fetchone()[0]
        selected=[]
        for provider,values in [('google_weather',{'temperature_c':12,'cloud_cover_pct':30,'wind_speed_ms':2}),
            ('solcast',{'irradiance_global_wm2':100,'irradiance_direct_wm2':80,'irradiance_diffuse_wm2':20})]:
            row=ProviderWeatherInterval(provider,receipt+timedelta(hours=1),receipt+timedelta(hours=2),values)
            selected.append(str(store_forecast_capture(db,subject,capture_id=uuid4(),tenant_id=tenant,plant_id=plant,
                provider=provider,mapping_version='v1',captured_at=receipt,intervals=(row,))))
        body={'captureIds':selected,'forecastOriginUtc':receipt.isoformat(),'performanceRatio':.85,'temperatureCoefficientPerC':-.004}
        path='/dashboard/plants/'+plant+'/generation-preview'
        assert dashboard.post(path,json=body).status_code==401
        assert dashboard.post('/dashboard/plants/002/generation-preview',auth=auth,json=body).status_code==403
        success=dashboard.post(path,auth=auth,json=body)
        assert success.status_code==200
        result=success.json()['data']
        assert result['persistence']=='not_written' and result['accuracy']=='not_evaluated'
        assert len(result['points'])==1
        assert 'uncalibrated_candidate' in result['points'][0]['qualityFlags']
        assert dashboard.post(path,auth=auth,json=body|{'performanceRatio':True}).status_code==400
        assert dashboard.post(path,auth=auth,json=body|{'forecastOriginUtc':'2100-01-01T00:00:00Z'}).status_code==400
        assert dashboard.post(path,auth=auth,json=body|{'captureIds':[selected[0],str(uuid4())]}).status_code==403
        dashboard.patch('/dashboard/plants/'+plant+'/profile',auth=auth,json={'tiltDeg':None})
        missing=dashboard.post(path,auth=auth,json=body)
        assert missing.status_code==409 and missing.json()['error']['missingFields']==['tiltDeg']
        with psycopg.connect(db) as connection:
            assert connection.execute('SELECT count(*) FROM forecast_run').fetchone()[0]==before


def test_selected_capture_composition_checks_tenant_membership_and_origin(db):
    from app.captured_operational_weather import load_captured_operational_weather
    receipt=datetime(2026,10,4,10,tzinfo=timezone.utc)
    selected=[]
    for provider,values in [('google_weather',{'temperature_c':12,'cloud_cover_pct':30,'wind_speed_ms':2}),
        ('solcast',{'irradiance_global_wm2':100,'irradiance_direct_wm2':80,'irradiance_diffuse_wm2':20})]:
        step=60 if provider=='google_weather' else 30
        intervals=tuple(ProviderWeatherInterval(provider,receipt+timedelta(minutes=start),receipt+timedelta(minutes=start+step),values)
            for start in range(60,120,step))
        selected.append(store_forecast_capture(db,'alice',capture_id=uuid4(),tenant_id='a',plant_id='002',
            provider=provider,mapping_version='v1',captured_at=receipt,intervals=intervals))
    options=dict(database_url=db,tenant_id='a',plant_id='002',capture_ids=tuple(selected),forecast_origin=receipt)
    result=load_captured_operational_weather(subject='alice',**options)
    assert len(result.intervals)==1 and result.intervals[0].irradiance_global_wm2==100
    assert {s.capture_id for s in result.sources}==set(selected)
    with pytest.raises(PermissionError):load_captured_operational_weather(subject='bob',**options)
    with pytest.raises(PermissionError):load_captured_operational_weather(subject='alice',**{**options,'plant_id':'001'})
    with pytest.raises(PermissionError):load_captured_operational_weather(subject='alice',**{**options,'tenant_id':'b'})
    with pytest.raises(PermissionError):load_captured_operational_weather(subject='alice',**{**options,'capture_ids':(selected[0],uuid4())})
    with pytest.raises(ValueError):load_captured_operational_weather(subject='alice',**{**options,'forecast_origin':receipt-timedelta(seconds=1)})
    with psycopg.connect(db) as connection:
        connection.execute("UPDATE membership SET active=false WHERE tenant_id='a' AND subject='alice'")
    with pytest.raises(PermissionError):load_captured_operational_weather(subject='alice',**options)


def test_capture_job_retains_success_skips_slot_and_denies_foreign_scope(db):
    now=datetime(2026,10,4,10,tzinfo=timezone.utc)
    calls=[]
    def collector(database_url,subject,*,tenant_id,plant_id,provider):
        calls.append(provider)
        if provider=='solcast':raise RuntimeError('sensitive upstream text must not be retained')
        row=ProviderWeatherInterval(provider,now+timedelta(hours=1),now+timedelta(hours=2),{'cloud_cover_pct':40})
        store_forecast_capture(database_url,subject,capture_id=uuid4(),tenant_id=tenant_id,
            plant_id=plant_id,provider=provider,mapping_version='test-v1',captured_at=now,intervals=(row,))
        return {'intervalCount':1}
    options=dict(database_url=db,subject='alice',tenant_id='a',plant_ids=('002',),collector=collector,now=now)
    first=run_capture_job(**options)
    assert first[0]['status']=='captured'
    assert first[1]['status']=='failed'
    assert 'sensitive' not in str(first)
    second=run_capture_job(**options)
    assert second[0]['status']=='slot_already_captured'
    assert calls==['google_weather','solcast','solcast']
    denied=run_capture_job(**{**options,'subject':'bob'})
    assert all(o['errorClass']=='PermissionError' for o in denied)
    assert len(calls)==3


def test_passport_patch_preserves_other_fields_and_checks_owner(db):
    with psycopg.connect(db) as connection:
        connection.execute("INSERT INTO plant_profile(plant_id,tilt_deg,operator_notes) VALUES ('002',30,'keep')")
    options = dict(database_url=db,tenant_id='a',plant_id='002',changes={'latitude':50.54085,'longitude':30.62605,'timezone':'Europe/Kyiv'})
    with pytest.raises(PermissionError):
        update_plant_profile(subject='bob',**options)
    update_plant_profile(subject='alice',**options)
    saved = get_onboarding(database_url=db,subject='alice',tenant_id='a',plant_id='002')
    assert saved['latitude'] == 50.54085
    assert saved['longitude'] == 30.62605
    assert saved['tiltDeg'] == 30
    assert saved['operatorNotes'] == 'keep'
    with pytest.raises(ValueError):
        update_plant_profile(subject='alice',**{**options,'changes':{'latitude':91}})
    with pytest.raises(ValueError):
        update_plant_profile(subject='alice',**{**options,'changes':{'tenant_id':'b'}})
    with pytest.raises(ValueError):
        update_plant_profile(subject='alice',**{**options,'changes':{'timezone':'Invalid/Timezone'}})


def test_dashboard_passport_updates_existing_plant_without_duplication(db,keys,monkeypatch):
    monkeypatch.setenv('HIOS_DASHBOARD_USER','operator')
    monkeypatch.setenv('HIOS_DASHBOARD_PASSWORD','test-only-password')
    with TestClient(create_app(db,keys[1],'hios-test','hios-api')) as dashboard:
        auth=('operator','test-only-password')
        created=dashboard.post('/dashboard/plants',auth=auth,json={'name':'Passport test','tiltDeg':30})
        plant=created.json()['data']['id']
        path=f'/dashboard/plants/{plant}/profile'
        assert dashboard.patch(path,json={'latitude':50}).status_code == 401
        assert dashboard.patch(path,auth=auth,json={'latitude':50,'longitude':30}).status_code == 200
        saved=dashboard.get(path,auth=auth).json()['data']
        assert saved['tiltDeg'] == 30
        assert saved['latitude'] == 50
        assert 'cloudBindings' not in saved
        assert len(dashboard.get('/dashboard/plants',auth=auth).json()['data']) == 1


def test_collection_persists_future_rows_and_denies_foreign_plant_before_network(db):
    captured = datetime(2026,10,4,10,tzinfo=timezone.utc)
    with psycopg.connect(db) as connection:
        connection.execute("INSERT INTO plant_profile(plant_id,latitude,longitude) VALUES ('002',50,30)")
    class Reader:
        calls = 0
        def hourly_forecast(self, request):
            self.calls += 1
            return tuple(ProviderWeatherInterval('google_weather',captured+timedelta(hours=h),
                captured+timedelta(hours=h+1),{'cloud_cover_pct':40}) for h in (0,1,2))
    reader = Reader()
    options = dict(tenant_id='a',plant_id='002',provider='google_weather',reader=reader,clock=lambda:captured)
    with pytest.raises(PermissionError):
        collect_provider_forecast(db,'bob',**options)
    assert reader.calls == 0
    result = collect_provider_forecast(db,'alice',**options)
    assert result['intervalCount'] == 2
    assert result['excludedStartedIntervals'] == 1
    summaries = list_provider_captures(db,'alice',tenant_id='a',plant_id='002')
    assert summaries[0]['captureId'] == result['captureId']
    assert summaries[0]['providerIssuedAtUtc'] is None
    with pytest.raises(PermissionError):
        list_provider_captures(db,'bob',tenant_id='a',plant_id='002')


def test_provider_capture_is_idempotent_tenant_scoped_and_immutable(db):
    captured = datetime(2026,10,4,10,tzinfo=timezone.utc)
    row = ProviderWeatherInterval('google_weather',captured+timedelta(hours=1),
        captured+timedelta(hours=2),{'cloud_cover_pct':40,'temperature_c':20})
    options = dict(tenant_id='a',plant_id='002',provider='google_weather',
        mapping_version='google-v1',captured_at=captured,intervals=(row,))
    first = store_forecast_capture(db,'alice',capture_id=uuid4(),**options)
    assert store_forecast_capture(db,'alice',capture_id=uuid4(),**options) == first
    with pytest.raises(PermissionError):
        store_forecast_capture(db,'bob',capture_id=uuid4(),**options)
    with pytest.raises(PermissionError):
        store_forecast_capture(db,'alice',capture_id=uuid4(),**{**options,'plant_id':'001'})
    with psycopg.connect(db) as connection:
        assert connection.execute('SELECT count(*) FROM provider_forecast_capture').fetchone()[0] == 1
        saved = connection.execute('SELECT document FROM provider_forecast_capture').fetchone()[0]
        assert saved['provider_issued_at'] is None
        assert 'irradiance_global_wm2' not in saved['intervals'][0]['values']
    with psycopg.connect(db) as connection:
        with pytest.raises(psycopg.errors.RaiseException):
            connection.execute("UPDATE provider_forecast_capture SET mapping_version='rewritten'")


@pytest.fixture(scope="session")
def keys():
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    return private, public


@pytest.fixture
def db():
    url = os.environ["TEST_DATABASE_URL"]  # Required: never silently skip DB evidence.
    # Every test gets its own schema; no shared database truncation or deletion.
    schema = "test_" + uuid4().hex
    with psycopg.connect(url) as connection:
        connection.execute(psycopg.sql.SQL("CREATE SCHEMA {}").format(psycopg.sql.Identifier(schema)))
    test_url = psycopg.conninfo.make_conninfo(url, options=f"-c search_path={schema}")
    try:
        migrate(test_url)
        with psycopg.connect(test_url) as connection:
            connection.execute("INSERT INTO tenant VALUES ('a'), ('b')")
            connection.execute("INSERT INTO membership VALUES ('a','alice',true),('b','bob',true)")
            connection.execute("""INSERT INTO plant(public_id,tenant_id,name,capacity_kw) VALUES
                ('001','b','Private B',99),('002','a','A one',NULL),
                ('003','b','Private B two',20),('004','a','A two',120.5)""")
        yield test_url
    finally:
        with psycopg.connect(url) as connection:
            connection.execute(psycopg.sql.SQL("DROP SCHEMA {} CASCADE").format(psycopg.sql.Identifier(schema)))


@pytest.fixture
def client(db, keys):
    with TestClient(create_app(db, keys[1], "hios-test", "hios-api")) as value:
        yield value


def token(keys, **changes):
    claims = dict(sub="alice", tenant_id="a", iss="hios-test",
                  aud="hios-api", iat=int(time.time()), exp=int(time.time())+300)
    claims.update(changes)
    return jwt.encode({k: v for k, v in claims.items() if v is not None}, keys[0], algorithm="RS256")


def headers(keys, **changes):
    return {"Authorization": "Bearer " + token(keys, **changes)}


def contract(response, path):
    schema = SPEC["paths"][path]["get"]["responses"][str(response.status_code)]["content"]["application/json"]["schema"]
    Draft202012Validator({**SPEC, **schema}).validate(response.json())
    assert response.headers["X-Request-ID"]
    if response.status_code >= 400:
        assert response.json()["error"]["requestId"] == response.headers["X-Request-ID"]


def test_create_app_accepts_public_key_from_environment(monkeypatch, keys):
    monkeypatch.setenv("DATABASE_URL", "postgresql://invalid")
    monkeypatch.setenv("JWT_PUBLIC_KEY", keys[1])
    monkeypatch.delenv("JWT_PUBLIC_KEY_FILE", raising=False)
    monkeypatch.setenv("JWT_ISSUER", "hios-test")
    monkeypatch.setenv("JWT_AUDIENCE", "hios-api")
    with TestClient(create_app()) as app:
        assert app.get("/health").status_code == 200


def test_liveness_and_contract(client):
    response = client.get("/health")
    assert response.status_code == 200
    contract(response, "/health")
    assert client.get("/openapi.json").json() == SPEC


def test_filter_before_pagination_and_no_tenant_override(client, keys):
    response = client.get("/plants?limit=1&offset=1&tenant_id=b",
                          headers={**headers(keys), "X-Tenant-ID": "b"})
    assert response.status_code == 200
    assert response.json() == {"data": [{"id": "004", "name": "A two", "capacityKw": 120.5}],
                               "limit": 1, "offset": 1}
    contract(response, "/plants")


def test_both_tenants_and_unknown_capacity(client, keys):
    a = client.get("/plants", headers=headers(keys))
    b = client.get("/plants", headers=headers(keys, sub="bob", tenant_id="b"))
    assert {x["id"] for x in a.json()["data"]} == {"002", "004"}
    assert {x["id"] for x in b.json()["data"]} == {"001", "003"}
    assert "capacityKw" not in a.json()["data"][0]
    contract(a, "/plants")
    contract(b, "/plants")


def test_empty_page(client, keys):
    response = client.get("/plants?offset=100", headers=headers(keys))
    assert response.status_code == 200
    assert response.json()["data"] == []
    contract(response, "/plants")


@pytest.mark.parametrize("changes", [
    {"exp": 1}, {"exp": None}, {"iss": "wrong"}, {"aud": "wrong"},
    {"sub": None}, {"iat": int(time.time())+3600}, {"sub": ""},
])
def test_invalid_identity(client, keys, changes):
    response = client.get("/plants", headers=headers(keys, **changes))
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    contract(response, "/plants")


@pytest.mark.parametrize("authorization", ["", "Bearer invalid", "Basic abc", "Bearer a b"])
def test_missing_or_malformed_token(client, authorization):
    response = client.get("/plants", headers={"Authorization": authorization})
    assert response.status_code == 401
    contract(response, "/plants")


def test_wrong_signature_and_algorithm(client, keys):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    bad = token((other, keys[1]))
    for encoded in [bad, jwt.encode({"sub": "alice"}, "x"*32, algorithm="HS256")]:
        response = client.get("/plants", headers={"Authorization": "Bearer " + encoded})
        assert response.status_code == 401
        contract(response, "/plants")


@pytest.mark.parametrize("changes", [{"tenant_id": "b"}, {"tenant_id": None}, {"tenant_id": "missing"}])
def test_forbidden_tenant(client, keys, changes):
    response = client.get("/plants", headers=headers(keys, **changes))
    assert response.status_code == 403
    contract(response, "/plants")


def test_revoked_membership(client, db, keys):
    with psycopg.connect(db) as connection:
        connection.execute("UPDATE membership SET active=false WHERE subject='alice'")
    assert client.get("/plants", headers=headers(keys)).status_code == 403


@pytest.mark.parametrize("query", ["limit=0", "limit=101", "limit=-1", "limit=1.5",
                                    "offset=-1", "offset=2147483648", "limit=1&limit=2",
                                    "limit=abc", "offset="])
def test_invalid_paging(client, keys, query):
    response = client.get("/plants?" + query, headers=headers(keys))
    assert response.status_code == 400
    contract(response, "/plants")


def test_migration_idempotence_and_constraints(db):
    migrate(db)
    with psycopg.connect(db) as connection:
        assert connection.execute("SELECT count(*) FROM schema_migration").fetchone()[0] == len(
            list(Path("migrations").glob("*.sql"))
        )
    for value in [-1, float("inf"), float("nan")]:
        with pytest.raises(psycopg.errors.CheckViolation):
            with psycopg.connect(db) as connection:
                connection.execute("INSERT INTO plant VALUES ('bad','a','Bad',%s)", (value,))


def forecast_run(run_id, **changes):
    values = dict(
        run_id=run_id, tenant_id="a", plant_id="002",
        forecast_origin_utc=datetime.fromisoformat("2026-09-06T00:00:00+00:00"),
        horizon_id="day_ahead", model_id="MODEL-001", model_version="0.1.0",
        feature_version="features-1", input_hash="a" * 64,
        configuration_hash="b" * 64, code_commit="abcdef1", status="normal",
    )
    values.update(changes)
    return ForecastRun(**values)


def test_forecast_run_is_idempotent_and_tenant_safe(db):
    first = forecast_run(uuid4())
    assert create_or_get_run(db, "alice", first) == first.run_id
    retry = forecast_run(uuid4())
    assert create_or_get_run(db, "alice", retry) == first.run_id
    with psycopg.connect(db) as connection:
        assert connection.execute("SELECT count(*) FROM forecast_run").fetchone()[0] == 1
    with pytest.raises(PermissionError):
        create_or_get_run(db, "bob", forecast_run(uuid4()))
    with pytest.raises(PermissionError):
        create_or_get_run(db, "alice", forecast_run(uuid4(), plant_id="001"))


def test_forecast_storage_constraints(db):
    run = forecast_run(uuid4())
    create_or_get_run(db, "alice", run)
    with psycopg.connect(db) as connection:
        connection.execute("""INSERT INTO forecast_point(
            run_id, interval_start_utc, interval_end_utc, predicted_power_kw,
            predicted_energy_kwh) VALUES (%s, %s, %s, 10, 10)""",
            (run.run_id, run.forecast_origin_utc, run.forecast_origin_utc.replace(hour=1)))
    with pytest.raises(psycopg.errors.CheckViolation):
        with psycopg.connect(db) as connection:
            connection.execute("""INSERT INTO forecast_point(
                run_id, interval_start_utc, interval_end_utc, predicted_power_kw,
                predicted_energy_kwh) VALUES (%s, %s, %s, -1, 0)""",
                (run.run_id, run.forecast_origin_utc.replace(hour=1), run.forecast_origin_utc))


def test_forecast_point_publication_is_idempotent_and_tenant_safe(db):
    run = forecast_run(uuid4())
    create_or_get_run(db, "alice", run)
    point = ForecastPoint(
        interval_start_utc=run.forecast_origin_utc,
        interval_end_utc=run.forecast_origin_utc.replace(hour=1),
        predicted_power_kw=10, predicted_energy_kwh=10,
        quality_flags=("weather_degraded",), provider_provenance={"weather": "snapshot-1"},
    )
    assert publish_points(db, "alice", "a", run.run_id, (point,)) == 1
    assert publish_points(db, "alice", "a", run.run_id, (point,)) == 0
    with psycopg.connect(db) as connection:
        assert connection.execute("SELECT quality_flags, provider_provenance FROM forecast_point").fetchone() == (
            ["weather_degraded"], {"weather": "snapshot-1"}
        )
    with pytest.raises(PermissionError):
        publish_points(db, "bob", "a", run.run_id, (point,))


def test_forecast_point_publication_rejects_blocked_runs_and_invalid_batches(db):
    blocked = forecast_run(uuid4(), status="blocked")
    create_or_get_run(db, "alice", blocked)
    point = ForecastPoint(
        interval_start_utc=blocked.forecast_origin_utc,
        interval_end_utc=blocked.forecast_origin_utc.replace(hour=1),
        predicted_power_kw=0, predicted_energy_kwh=0,
    )
    with pytest.raises(PermissionError):
        publish_points(db, "alice", "a", blocked.run_id, (point,))
    with pytest.raises(ValueError, match="at least one"):
        publish_points(db, "alice", "a", blocked.run_id, ())
    invalid = ForecastPoint(
        interval_start_utc=blocked.forecast_origin_utc,
        interval_end_utc=blocked.forecast_origin_utc.replace(hour=1),
        predicted_power_kw=-1, predicted_energy_kwh=0,
    )
    with pytest.raises(ValueError, match="finite non-negative"):
        publish_points(db, "alice", "a", blocked.run_id, (invalid,))


def test_forecast_run_read_api_is_tenant_scoped_and_read_only(client, db, keys):
    run = forecast_run(uuid4())
    create_or_get_run(db, "alice", run)
    publish_points(db, "alice", "a", run.run_id, (ForecastPoint(
        interval_start_utc=run.forecast_origin_utc,
        interval_end_utc=run.forecast_origin_utc + timedelta(hours=1),
        predicted_power_kw=12.5, predicted_energy_kwh=12.5,
        quality_flags=("source_verified",), provider_provenance={"weather": "solcast"},
    ),))

    response = client.get(f"/forecast-runs/{run.run_id}?limit=1", headers=headers(keys))

    assert response.status_code == 200
    assert response.json()["data"] == {
        "id": str(run.run_id), "plantId": "002",
        "forecastOriginUtc": "2026-09-06T00:00:00+00:00", "horizonId": "day_ahead",
        "modelId": "MODEL-001", "modelVersion": "0.1.0",
        "featureVersion": "features-1", "status": "normal",
        "points": [{
            "intervalStartUtc": "2026-09-06T00:00:00+00:00",
            "intervalEndUtc": "2026-09-06T01:00:00+00:00",
            "predictedPowerKw": 12.5, "predictedEnergyKwh": 12.5,
            "qualityFlags": ["source_verified"], "providerProvenance": {"weather": "solcast"},
        }],
    }
    contract(response, "/forecast-runs/{run_id}")
    assert client.get(f"/forecast-runs/{run.run_id}", headers=headers(keys, sub="bob", tenant_id="b")).status_code == 404
    assert client.get("/forecast-runs/not-a-uuid", headers=headers(keys)).status_code == 400
    assert client.get(f"/forecast-runs/{run.run_id}?limit=0", headers=headers(keys)).status_code == 400


def test_plant_forecast_run_list_is_tenant_scoped_newest_first(client, db, keys):
    earlier = forecast_run(uuid4())
    later = forecast_run(uuid4(), forecast_origin_utc=earlier.forecast_origin_utc + timedelta(hours=1))
    create_or_get_run(db, "alice", earlier)
    create_or_get_run(db, "alice", later)
    publish_points(db, "alice", "a", earlier.run_id, (ForecastPoint(
        interval_start_utc=earlier.forecast_origin_utc,
        interval_end_utc=earlier.forecast_origin_utc + timedelta(hours=1),
        predicted_power_kw=1, predicted_energy_kwh=1,
    ),))

    response = client.get("/plants/002/forecast-runs?limit=1", headers=headers(keys))

    assert response.status_code == 200
    assert response.json() == {"data": [{
        "id": str(later.run_id), "forecastOriginUtc": "2026-09-06T01:00:00+00:00",
        "horizonId": "day_ahead", "modelId": "MODEL-001", "modelVersion": "0.1.0",
        "featureVersion": "features-1", "status": "normal", "pointCount": 0,
    }], "limit": 1, "offset": 0}
    contract(response, "/plants/{plant_id}/forecast-runs")
    assert client.get("/plants/001/forecast-runs", headers=headers(keys)).status_code == 404
    assert client.get("/plants/missing/forecast-runs", headers=headers(keys)).status_code == 404
    assert client.get("/plants/002/forecast-runs?offset=-1", headers=headers(keys)).status_code == 400


def model_candidate(**changes):
    values = dict(
        tenant_id="a", plant_id="002", model_id="MODEL-001", model_version="0.1.0-candidate",
        model_type="deterministic_physical", feature_schema_version="model-001-features-v1",
        configuration_hash="d" * 64, code_commit="abcdef1",
        training_dataset_ref="not-applicable-deterministic",
    )
    values.update(changes)
    return ModelCandidate(**values)


def test_model_candidate_registry_is_immutable_and_tenant_safe(db):
    candidate = model_candidate()
    assert register_candidate(db, "alice", candidate) is True
    assert register_candidate(db, "alice", candidate) is False
    with pytest.raises(PermissionError):
        register_candidate(db, "bob", model_candidate())
    with pytest.raises(psycopg.errors.CheckViolation):
        with psycopg.connect(db) as connection:
            connection.execute("""UPDATE model_registry SET state='approved'
                WHERE tenant_id='a' AND plant_id='002'""")
    with psycopg.connect(db) as connection:
        connection.execute("""UPDATE model_registry SET state='approved', approved_by='reviewer',
            approved_at=now(), decision_ref='decision-1' WHERE tenant_id='a' AND plant_id='002'""")
    resolved = resolve_approved_candidate(db, "alice", "a", "002", "MODEL-001")
    assert resolved.model_version == "0.1.0-candidate"
    with pytest.raises(PermissionError):
        resolve_approved_candidate(db, "bob", "a", "002", "MODEL-001")


def test_model_001_job_binds_approved_lineage_and_publishes_idempotently(db):
    geometry = PlantGeometry(50.45, 30.52, 30, 180)
    config = Model001Config("0.1.0-candidate", 100, 80, 0.8, -0.004)
    weather = normalize_weather(
        provider="fixture", product="forecast", mapping_version="v1",
        provider_issued_at=datetime(2026, 6, 21, 8, tzinfo=timezone.utc),
        valid_at=datetime(2026, 6, 21, 9, tzinfo=timezone.utc),
        interval_end=datetime(2026, 6, 21, 10, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 6, 21, 8, tzinfo=timezone.utc),
        ghi=700, ghi_unit="W/m2", cloud_cover=20, cloud_cover_unit="%",
        temperature=25, temperature_unit="C", dni=600, dhi=100,
    )
    inputs = (ForecastWeatherInput("snapshot-001", weather),)
    candidate = model_candidate(configuration_hash=configuration_hash(config, geometry))
    register_candidate(db, "alice", candidate)
    with psycopg.connect(db) as connection:
        connection.execute("""UPDATE model_registry SET state='approved', approved_by='reviewer',
            approved_at=now(), decision_ref='decision-2' WHERE tenant_id='a' AND plant_id='002'""")
    run = forecast_run(uuid4(), forecast_origin_utc=datetime(2026, 6, 21, 8, tzinfo=timezone.utc),
                       input_hash=input_hash(inputs), configuration_hash=candidate.configuration_hash,
                       feature_version="model-001-features-v1", model_version=config.model_version)
    first = execute_model_001(database_url=db, subject="alice", run=run, config=config,
                              geometry=geometry, weather_inputs=inputs)
    second = execute_model_001(database_url=db, subject="alice", run=run, config=config,
                               geometry=geometry, weather_inputs=inputs)
    assert first.run_id == run.run_id and first.published_points == 1
    assert second.run_id == run.run_id and second.published_points == 0
    with psycopg.connect(db) as connection:
        assert connection.execute("SELECT count(*) FROM forecast_point WHERE run_id=%s", (run.run_id,)).fetchone()[0] == 1


def test_model_001_job_rejects_unapproved_or_changed_lineage(db):
    geometry = PlantGeometry(50.45, 30.52, 30, 180)
    config = Model001Config("0.1.0-candidate", 100, 80, 0.8, -0.004)
    weather = normalize_weather(
        provider="fixture", product="forecast", mapping_version="v1",
        provider_issued_at=datetime(2026, 6, 21, 8, tzinfo=timezone.utc),
        valid_at=datetime(2026, 6, 21, 9, tzinfo=timezone.utc),
        interval_end=datetime(2026, 6, 21, 10, tzinfo=timezone.utc),
        retrieved_at=datetime(2026, 6, 21, 8, tzinfo=timezone.utc),
        ghi=700, ghi_unit="W/m2", cloud_cover=20, cloud_cover_unit="%",
        temperature=25, temperature_unit="C", dni=600, dhi=100,
    )
    inputs = (ForecastWeatherInput("snapshot-001", weather),)
    run = forecast_run(uuid4(), forecast_origin_utc=datetime(2026, 6, 21, 8, tzinfo=timezone.utc),
                       input_hash=input_hash(inputs), configuration_hash=configuration_hash(config, geometry),
                       feature_version="model-001-features-v1", model_version=config.model_version)
    with pytest.raises(PermissionError, match="No approved"):
        execute_model_001(database_url=db, subject="alice", run=run, config=config,
                          geometry=geometry, weather_inputs=inputs)


def test_forecast_schedule_uses_utc_alignment_and_explicit_delay():
    spec = ScheduleSpec("day_ahead", cadence_minutes=60, publication_delay_minutes=10)
    assert latest_due_origin(datetime(2026, 9, 7, 10, 5, tzinfo=timezone.utc), spec) == datetime(
        2026, 9, 7, 9, tzinfo=timezone.utc
    )
    with pytest.raises(ValueError):
        latest_due_origin(datetime(2026, 9, 7, 10, 5), spec)


def test_forecast_job_lease_is_scoped_renewable_and_releasable(db):
    key = JobKey("a", "002", datetime(2026, 9, 7, 9, tzinfo=timezone.utc), "day_ahead")
    first, second = uuid4(), uuid4()
    assert claim_lease(db, "alice", key, first) is True
    assert claim_lease(db, "alice", key, first) is True
    assert claim_lease(db, "alice", key, second) is False
    with pytest.raises(PermissionError):
        claim_lease(db, "bob", key, second)
    assert release_lease(db, "alice", key, second) is False
    assert release_lease(db, "alice", key, first) is True
    assert claim_lease(db, "alice", key, second) is True


def test_worker_attempt_releases_lease_and_records_minimal_success_outcome(db):
    geometry = PlantGeometry(50.45, 30.52, 30, 180)
    config = Model001Config("0.1.0-candidate", 100, 80, 0.8, -0.004)
    origin = datetime(2026, 6, 21, 8, tzinfo=timezone.utc)
    weather = normalize_weather(
        provider="fixture", product="forecast", mapping_version="v1", provider_issued_at=origin,
        valid_at=origin.replace(hour=9), interval_end=origin.replace(hour=10), retrieved_at=origin,
        ghi=700, ghi_unit="W/m2", cloud_cover=20, cloud_cover_unit="%", temperature=25,
        temperature_unit="C", dni=600, dhi=100,
    )
    inputs = (ForecastWeatherInput("snapshot-001", weather),)
    candidate = model_candidate(configuration_hash=configuration_hash(config, geometry))
    register_candidate(db, "alice", candidate)
    with psycopg.connect(db) as connection:
        connection.execute("""UPDATE model_registry SET state='approved', approved_by='reviewer',
            approved_at=now(), decision_ref='decision-worker' WHERE tenant_id='a' AND plant_id='002'""")
    run = forecast_run(uuid4(), forecast_origin_utc=origin, input_hash=input_hash(inputs),
                       configuration_hash=candidate.configuration_hash, feature_version="model-001-features-v1",
                       model_version=config.model_version)
    key = JobKey("a", "002", origin, "day_ahead")
    attempt = run_once(database_url=db, subject="alice", key=key, lease_id=uuid4(), run=run,
                       config=config, geometry=geometry, weather_inputs=inputs)
    assert attempt.status == "succeeded" and attempt.run_id == run.run_id and attempt.published_points == 1
    with psycopg.connect(db) as connection:
        assert connection.execute("SELECT status, error_class FROM forecast_job_outcome").fetchone() == (
            "succeeded", None
        )
        assert connection.execute("SELECT count(*) FROM forecast_job_lease").fetchone()[0] == 0
    outcome_window_end = datetime.now(timezone.utc) + timedelta(minutes=1)
    outcome_window_start = outcome_window_end - timedelta(days=1)
    summary = summarize_outcomes(db, "alice", "a", "002", outcome_window_start, outcome_window_end)
    assert (summary.succeeded, summary.failed, summary.running, summary.published_points) == (1, 0, 0, 1)
    with pytest.raises(PermissionError):
        summarize_outcomes(db, "bob", "a", "002", outcome_window_start, outcome_window_end)


def test_worker_records_failed_outcome_and_releases_lease(db):
    origin = datetime(2026, 6, 21, 8, tzinfo=timezone.utc)
    geometry = PlantGeometry(50.45, 30.52, 30, 180)
    config = Model001Config("0.1.0-candidate", 100, 80, 0.8, -0.004)
    weather = normalize_weather(
        provider="fixture", product="forecast", mapping_version="v1", provider_issued_at=origin,
        valid_at=origin.replace(hour=9), interval_end=origin.replace(hour=10), retrieved_at=origin,
        ghi=700, ghi_unit="W/m2", cloud_cover=20, cloud_cover_unit="%", temperature=25,
        temperature_unit="C", dni=600, dhi=100,
    )
    inputs = (ForecastWeatherInput("snapshot-001", weather),)
    run = forecast_run(uuid4(), forecast_origin_utc=origin, input_hash=input_hash(inputs),
                       configuration_hash=configuration_hash(config, geometry),
                       feature_version="model-001-features-v1", model_version=config.model_version)
    key = JobKey("a", "002", origin, "day_ahead")
    with pytest.raises(PermissionError, match="No approved"):
        run_once(database_url=db, subject="alice", key=key, lease_id=uuid4(), run=run,
                 config=config, geometry=geometry, weather_inputs=inputs)
    with psycopg.connect(db) as connection:
        assert connection.execute("SELECT status, error_class FROM forecast_job_outcome").fetchone() == (
            "failed", "PermissionError"
        )
        assert connection.execute("SELECT count(*) FROM forecast_job_lease").fetchone()[0] == 0


def weather_snapshot(snapshot_id, **changes):
    weather = normalize_weather(
        provider="provider-role", product="forecast", mapping_version="v1",
        provider_issued_at=datetime.fromisoformat("2026-09-06T00:00:00+00:00"),
        valid_at=datetime.fromisoformat("2026-09-06T01:00:00+00:00"),
        interval_end=datetime.fromisoformat("2026-09-06T02:00:00+00:00"),
        retrieved_at=datetime.fromisoformat("2026-09-06T00:01:00+00:00"),
        ghi=400, ghi_unit="W/m2", cloud_cover=20, cloud_cover_unit="%",
        temperature=20, temperature_unit="C",
    )
    values = dict(snapshot_id=snapshot_id, tenant_id="a", plant_id="002",
                  source_reference="provider-request-123", payload_sha256="c" * 64,
                  weather=weather)
    values.update(changes)
    return WeatherSnapshot(**values)


def test_weather_snapshot_is_idempotent_and_tenant_safe(db):
    first = weather_snapshot(uuid4())
    assert create_or_get_snapshot(db, "alice", first) == first.snapshot_id
    assert create_or_get_snapshot(db, "alice", weather_snapshot(uuid4())) == first.snapshot_id
    with psycopg.connect(db) as connection:
        assert connection.execute("SELECT count(*) FROM weather_snapshot").fetchone()[0] == 1
    with pytest.raises(PermissionError):
        create_or_get_snapshot(db, "bob", weather_snapshot(uuid4()))
    with pytest.raises(PermissionError):
        create_or_get_snapshot(db, "alice", weather_snapshot(uuid4(), plant_id="001"))


def test_weather_snapshot_retains_field_level_provider_provenance(db):
    snapshot = weather_snapshot(uuid4(), provider_provenance={
        "cloud_cover_pct": "google_weather",
        "irradiance_global_wm2": "solcast",
    })
    create_or_get_snapshot(db, "alice", snapshot)

    with psycopg.connect(db) as connection:
        assert connection.execute("SELECT provider_provenance FROM weather_snapshot").fetchone()[0] == {
            "cloud_cover_pct": "google_weather", "irradiance_global_wm2": "solcast",
        }

    with pytest.raises(ValueError, match="provider_provenance"):
        create_or_get_snapshot(db, "alice", weather_snapshot(uuid4(), provider_provenance={"": "solcast"}))


def actual_snapshot(snapshot_id, **changes):
    start = datetime(2026, 9, 9, 10, tzinfo=timezone.utc)
    observation = ActualGenerationObservation(
        provider="deye_cloud", mapping_version="deye-actuals-v1",
        observed_at_utc=start, interval_end_utc=start + timedelta(hours=1),
        retrieved_at_utc=start + timedelta(hours=2), ac_power_kw=12.5,
        energy_kwh=12.5, energy_semantics=EnergySemantics.INTERVAL,
        quality_flags=("source_verified",),
    )
    values = dict(
        snapshot_id=snapshot_id, tenant_id="a", plant_id="002",
        source_reference="restricted-source-record-1", payload_sha256="e" * 64,
        observation=observation,
    )
    values.update(changes)
    return ActualGenerationSnapshot(**values)


def test_actual_generation_snapshot_is_idempotent_and_tenant_safe(db):
    first = actual_snapshot(uuid4())
    assert create_or_get_actual_snapshot(db, "alice", first) == first.snapshot_id
    assert create_or_get_actual_snapshot(db, "alice", actual_snapshot(uuid4())) == first.snapshot_id
    with psycopg.connect(db) as connection:
        assert connection.execute(
            "SELECT ac_power_kw, energy_kwh, energy_semantics, quality_flags FROM actual_generation_snapshot"
        ).fetchone() == (12.5, 12.5, "interval", ["source_verified"])
    with pytest.raises(PermissionError):
        create_or_get_actual_snapshot(db, "bob", actual_snapshot(uuid4()))
    with pytest.raises(PermissionError):
        create_or_get_actual_snapshot(db, "alice", actual_snapshot(uuid4(), plant_id="001"))


def test_actual_alignment_uses_exact_intervals_and_as_of_known_revision(db):
    run = forecast_run(uuid4())
    create_or_get_run(db, "alice", run)
    point = ForecastPoint(
        interval_start_utc=run.forecast_origin_utc,
        interval_end_utc=run.forecast_origin_utc + timedelta(hours=1),
        predicted_power_kw=10, predicted_energy_kwh=10,
    )
    publish_points(db, "alice", "a", run.run_id, (point,))
    initial = actual_snapshot(
        uuid4(),
        observation=ActualGenerationObservation(
            provider="deye_cloud", mapping_version="deye-actuals-v1",
            observed_at_utc=run.forecast_origin_utc,
            interval_end_utc=run.forecast_origin_utc + timedelta(hours=1),
            retrieved_at_utc=run.forecast_origin_utc + timedelta(hours=2),
            ac_power_kw=12.5, energy_kwh=12.5, energy_semantics=EnergySemantics.INTERVAL,
        ),
    )
    create_or_get_actual_snapshot(db, "alice", initial)
    early = load_aligned_power_samples(
        database_url=db, subject="alice", tenant_id="a", plant_id="002", run_id=run.run_id,
        actual_provider="deye_cloud", actual_mapping_version="deye-actuals-v1",
        actuals_as_of_utc=run.forecast_origin_utc + timedelta(hours=1),
    )
    assert early == ()
    known = load_aligned_power_samples(
        database_url=db, subject="alice", tenant_id="a", plant_id="002", run_id=run.run_id,
        actual_provider="deye_cloud", actual_mapping_version="deye-actuals-v1",
        actuals_as_of_utc=run.forecast_origin_utc + timedelta(hours=3),
    )
    assert known[0].actual_power_kw == 12.5
    revised = actual_snapshot(
        uuid4(), payload_sha256="f" * 64,
        observation=ActualGenerationObservation(
            provider="deye_cloud", mapping_version="deye-actuals-v1",
            observed_at_utc=run.forecast_origin_utc,
            interval_end_utc=run.forecast_origin_utc + timedelta(hours=1),
            retrieved_at_utc=run.forecast_origin_utc + timedelta(hours=4),
            ac_power_kw=15, energy_kwh=15, energy_semantics=EnergySemantics.INTERVAL,
        ),
    )
    create_or_get_actual_snapshot(db, "alice", revised)
    latest = load_aligned_power_samples(
        database_url=db, subject="alice", tenant_id="a", plant_id="002", run_id=run.run_id,
        actual_provider="deye_cloud", actual_mapping_version="deye-actuals-v1",
        actuals_as_of_utc=run.forecast_origin_utc + timedelta(hours=5),
    )
    assert latest[0].actual_power_kw == 15
    with pytest.raises(PermissionError):
        load_aligned_power_samples(
            database_url=db, subject="bob", tenant_id="a", plant_id="002", run_id=run.run_id,
            actual_provider="deye_cloud", actual_mapping_version="deye-actuals-v1",
            actuals_as_of_utc=run.forecast_origin_utc + timedelta(hours=5),
        )


def test_database_failure_is_safe_and_health_independent(keys):
    with TestClient(create_app("postgresql://invalid:invalid@127.0.0.1:1/missing",
                               keys[1], "hios-test", "hios-api")) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/plants", headers=headers(keys))
        assert response.status_code == 500
        contract(response, "/plants")
        assert response.json()["error"]["message"] == "Internal error"


def test_migration_checksum_change_fails_closed(db):
    with psycopg.connect(db) as connection:
        connection.execute("UPDATE schema_migration SET checksum='changed'")
    with pytest.raises(ValueError, match="Applied migration changed"):
        migrate(db)



def test_forecast_dashboard_is_public_and_credentials_free(keys):
    with TestClient(create_app("postgresql://invalid", keys[1], "hios-test", "hios-api")) as public:
        response = public.get("/")
        assert response.status_code == 200
        assert "HIOS Forecast" in response.text
        assert "SOLCAST_API_KEY" not in response.text
        assert "GOOGLE_WEATHER_API_KEY" not in response.text
        assert public.get("/assets/app.js").status_code == 200
        assert public.get("/assets/styles.css").status_code == 200


def test_dashboard_can_require_basic_access(keys, monkeypatch):
    monkeypatch.setenv("HIOS_DASHBOARD_USER", "operator")
    monkeypatch.setenv("HIOS_DASHBOARD_PASSWORD", "test-only-password")
    with TestClient(create_app("postgresql://invalid", keys[1], "hios-test", "hios-api")) as guarded:
        denied = guarded.get("/")
        assert denied.status_code == 401
        assert denied.headers["WWW-Authenticate"] == 'Basic realm="HIOS Forecast"'
        assert guarded.get("/assets/app.js").status_code == 401
        assert guarded.get("/health").status_code == 200
        granted = guarded.get("/", auth=("operator", "test-only-password"))
        assert granted.status_code == 200
        assert "HIOS Forecast" in granted.text


def test_dashboard_basic_access_supports_utf8_credentials(keys, monkeypatch):
    monkeypatch.setenv("HIOS_DASHBOARD_USER", "оператор")
    monkeypatch.setenv("HIOS_DASHBOARD_PASSWORD", "надійний-пароль")
    with TestClient(create_app("postgresql://invalid", keys[1], "hios-test", "hios-api")) as guarded:
        response = guarded.get("/", auth=("оператор", "надійний-пароль"))
        assert response.status_code == 200
        assert "HIOS Forecast" in response.text

def test_real_http_server(db, keys):
    import socket
    import threading
    import httpx
    import uvicorn

    app = create_app(db, keys[1], "hios-test", "hios-api")
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.05)
        assert server.started
        url = f"http://127.0.0.1:{listener.getsockname()[1]}"
        response = httpx.get(url + "/health")
        assert response.status_code == 200
        contract(response, "/health")
        response = httpx.get(url + "/plants", headers=headers(keys))
        assert response.status_code == 200
        assert [p["id"] for p in response.json()["data"]] == ["002", "004"]
        contract(response, "/plants")
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
    assert not thread.is_alive()


def test_plant_onboarding_api_creates_and_exposes_only_metadata(client, keys):
    created = client.post("/plants", headers=headers(keys), json={
        "name": "API solar site", "capacityKw": 20, "latitude": 50.2, "longitude": 30.3,
        "timezone": "Europe/Kyiv", "meterBoundary": "grid export",
    })
    assert created.status_code == 201
    plant_id = created.json()["data"]["id"]
    binding = client.post(f"/plants/{plant_id}/cloud-bindings", headers=headers(keys), json={
        "provider": "deye_cloud", "externalPlantId": "restricted-native-id",
        "credentialReference": "keyvault://deye/a", "consentRecordReference": "consent-a",
        "mappingVersion": "deye-v1", "discoveryStatus": "pending",
    })
    assert binding.status_code == 201
    read = client.get(f"/plants/{plant_id}/onboarding", headers=headers(keys))
    assert read.status_code == 200
    assert read.json()["data"]["cloudBindings"][0]["readOnly"] is True
    assert client.get(f"/plants/{plant_id}/onboarding", headers=headers(keys, sub="bob", tenant_id="b")).status_code == 404


@pytest.mark.parametrize('status',['verified','blocked',None,True])
def test_binding_registration_cannot_claim_server_verification(client,db,keys,status):
    response=client.post('/plants/002/cloud-bindings',headers=headers(keys),json={
        'provider':'deye_cloud','externalPlantId':'7','credentialReference':'server-secret',
        'consentRecordReference':'consent','mappingVersion':'deye-v1','discoveryStatus':status})
    assert response.status_code==400
    with psycopg.connect(db) as connection:
        assert connection.execute('SELECT count(*) FROM inverter_cloud_binding').fetchone()[0]==0


def test_dashboard_can_create_its_isolated_plant_registry(db, keys, monkeypatch):
    monkeypatch.setenv("HIOS_DASHBOARD_USER", "operator")
    monkeypatch.setenv("HIOS_DASHBOARD_PASSWORD", "test-only-password")
    with TestClient(create_app(db, keys[1], "hios-test", "hios-api")) as dashboard:
        created = dashboard.post("/dashboard/plants", auth=("operator", "test-only-password"), json={
            "name": "Dashboard plant", "capacityKw": 25, "latitude": 50.2, "longitude": 30.2,
        })
        assert created.status_code == 201
        plants = dashboard.get("/dashboard/plants", auth=("operator", "test-only-password"))
        assert plants.status_code == 200
        assert plants.json()["data"][0]["name"] == "Dashboard plant"
        assert dashboard.get("/dashboard/plants").status_code == 401


def test_dashboard_can_select_weather_research_channel(db, keys, monkeypatch):
    monkeypatch.setenv("HIOS_DASHBOARD_USER", "operator")
    monkeypatch.setenv("HIOS_DASHBOARD_PASSWORD", "test-only-password")
    with TestClient(create_app(db, keys[1], "hios-test", "hios-api")) as dashboard:
        response = dashboard.post("/dashboard/weather-providers", auth=("operator", "test-only-password"), json={
            "provider": "eosda_weather", "role": "research"
        })
        assert response.status_code == 201
        channels = dashboard.get("/dashboard/weather-providers", auth=("operator", "test-only-password"))
        assert channels.json()["data"][0]["id"] == "eosda_weather"
        assert dashboard.post("/dashboard/weather-providers", auth=("operator", "test-only-password"), json={
            "provider": "not-real", "role": "research"
        }).status_code == 400


def test_dashboard_can_request_read_only_deye_connection(db, keys, monkeypatch):
    monkeypatch.setenv("HIOS_DASHBOARD_USER", "operator")
    monkeypatch.setenv("HIOS_DASHBOARD_PASSWORD", "test-only-password")
    with TestClient(create_app(db, keys[1], "hios-test", "hios-api")) as dashboard:
        plant = dashboard.post("/dashboard/plants", auth=("operator", "test-only-password"), json={"name": "Cloud candidate"})
        plant_id = plant.json()["data"]["id"]
        create = dashboard.post(f"/dashboard/plants/{plant_id}/cloud-requests", auth=("operator", "test-only-password"), json={"provider": "deye_cloud"})
        assert create.status_code == 201
        requests = dashboard.get(f"/dashboard/plants/{plant_id}/cloud-requests", auth=("operator", "test-only-password"))
        assert requests.json()["data"][0]["status"] == "awaiting_authorization"


def test_dashboard_can_register_a_plant_by_deye_id(db, keys, monkeypatch):
    monkeypatch.setenv("HIOS_DASHBOARD_USER", "operator")
    monkeypatch.setenv("HIOS_DASHBOARD_PASSWORD", "test-only-password")
    with TestClient(create_app(db, keys[1], "hios-test", "hios-api")) as dashboard:
        response=dashboard.post("/dashboard/plants/register-by-provider-id", auth=("operator", "test-only-password"), json={"provider":"deye_cloud","externalPlantId":"123456"})
        assert response.status_code==201
        assert response.json()["data"]["status"]=="awaiting_authorization"


def test_dashboard_can_register_a_plant_by_deye_station_link(db, keys, monkeypatch):
    monkeypatch.setenv("HIOS_DASHBOARD_USER", "operator")
    monkeypatch.setenv("HIOS_DASHBOARD_PASSWORD", "test-only-password")
    with TestClient(create_app(db, keys[1], "hios-test", "hios-api")) as dashboard:
        response = dashboard.post("/dashboard/plants/register-by-provider-id", auth=("operator", "test-only-password"), json={
            "provider": "deye_cloud", "externalPlantId": "https://www.deyecloud.com/station/basic?id=61205012"})
        assert response.status_code == 201
        plant = dashboard.get("/dashboard/plants", auth=("operator", "test-only-password")).json()["data"][0]
        assert plant["name"] == "Deye Cloud · 61205012"


def test_dashboard_lists_deye_stations_only_after_explicit_read_confirmation(db, keys, monkeypatch):
    monkeypatch.setenv("HIOS_DASHBOARD_USER", "operator")
    monkeypatch.setenv("HIOS_DASHBOARD_PASSWORD", "test-only-password")
    class FakeDeye:
        def obtain_token(self): return "token"
        def list_stations(self, token, *, page, size):
            return {"data": {"records": [{"stationName": "Погреби", "stationId": 7}]}}
    monkeypatch.setattr(main_module, "deye_client_from_environment", lambda: FakeDeye())
    with TestClient(create_app(db, keys[1], "hios-test", "hios-api")) as dashboard:
        assert dashboard.post("/dashboard/deye/stations/discover", auth=("operator", "test-only-password"), json={}).status_code == 400
        response = dashboard.post("/dashboard/deye/stations/discover", auth=("operator", "test-only-password"), json={"confirmReadOnly": True})
        assert response.status_code == 200
        assert response.json()["data"] == [{"id": "7", "name": "Погреби"}]


def test_hourly_plan_api_and_xlsx_export_are_tenant_scoped(client, db, keys):
    run = forecast_run(uuid4())
    create_or_get_run(db, "alice", run)
    publish_points(db, "alice", "a", run.run_id, (ForecastPoint(
        interval_start_utc=run.forecast_origin_utc,
        interval_end_utc=run.forecast_origin_utc + timedelta(hours=1),
        predicted_power_kw=12.5, predicted_energy_kwh=12.5,
        quality_flags=("source_verified",),
    ),))
    payload = {"consumptionKwh": [20], "rdnPriceUahPerKwh": [5.5]}
    response = client.post(f"/forecast-runs/{run.run_id}/hourly-plan", json=payload, headers=headers(keys))
    assert response.status_code == 200
    assert response.json()["data"][0]["netGridKwh"] == 7.5
    assert response.json()["data"][0]["estimatedImportCostUah"] == 41.25
    export = client.post(f"/forecast-runs/{run.run_id}/hourly-plan/export", json={**payload, "format": "xlsx"}, headers=headers(keys))
    assert export.status_code == 200
    assert export.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument")
    assert export.content[:2] == b"PK"
    assert client.post(f"/forecast-runs/{run.run_id}/hourly-plan", json=payload,
        headers=headers(keys, sub="bob", tenant_id="b")).status_code == 404


def test_dashboard_builds_and_exports_a_tenant_scoped_hourly_plan(db, keys, monkeypatch):
    import hashlib
    monkeypatch.setenv("HIOS_DASHBOARD_USER", "operator")
    monkeypatch.setenv("HIOS_DASHBOARD_PASSWORD", "test-only-password")
    tenant = "dashboard-" + hashlib.sha256(b"operator").hexdigest()[:24]
    with TestClient(create_app(db, keys[1], "hios-test", "hios-api")) as dashboard:
        created = dashboard.post("/dashboard/plants", auth=("operator", "test-only-password"), json={"name": "Dashboard plan"})
        plant_id = created.json()["data"]["id"]
        forecast = forecast_run(uuid4(), tenant_id=tenant, plant_id=plant_id)
        create_or_get_run(db, "operator", forecast)
        publish_points(db, "operator", tenant, forecast.run_id, (ForecastPoint(
            interval_start_utc=forecast.forecast_origin_utc,
            interval_end_utc=forecast.forecast_origin_utc + timedelta(hours=1),
            predicted_power_kw=10, predicted_energy_kwh=10,
        ),))
        runs = dashboard.get(f"/dashboard/plants/{plant_id}/forecast-runs", auth=("operator", "test-only-password"))
        assert runs.status_code == 200
        assert runs.json()["data"][0]["id"] == str(forecast.run_id)
        payload = {"consumptionKwh": [12], "rdnPriceUahPerKwh": [5]}
        plan = dashboard.post(f"/dashboard/forecast-runs/{forecast.run_id}/hourly-plan", auth=("operator", "test-only-password"), json=payload)
        assert plan.status_code == 200
        assert plan.json()["data"][0]["estimatedImportCostUah"] == 10
        export = dashboard.post(f"/dashboard/forecast-runs/{forecast.run_id}/hourly-plan/export", auth=("operator", "test-only-password"), json={**payload, "format": "xlsx"})
        assert export.status_code == 200 and export.content[:2] == b"PK"
        assert dashboard.get(f"/dashboard/plants/{plant_id}/forecast-runs").status_code == 401


def test_dashboard_can_save_rdn_scenario_and_apply_it_to_a_forecast(db, keys, monkeypatch):
    monkeypatch.setenv("HIOS_DASHBOARD_USER", "price-operator")
    monkeypatch.setenv("HIOS_DASHBOARD_PASSWORD", "test-only-password")
    import hashlib
    tenant = "dashboard-" + hashlib.sha256(b"price-operator").hexdigest()[:24]
    with TestClient(create_app(db, keys[1], "hios-test", "hios-api")) as dashboard:
        plant = dashboard.post("/dashboard/plants", auth=("price-operator", "test-only-password"), json={"name": "Price plan"}).json()["data"]["id"]
        run = forecast_run(uuid4(), tenant_id=tenant, plant_id=plant)
        create_or_get_run(db, "price-operator", run)
        publish_points(db, "price-operator", tenant, run.run_id, (ForecastPoint(
            interval_start_utc=run.forecast_origin_utc, interval_end_utc=run.forecast_origin_utc + timedelta(hours=1),
            predicted_power_kw=3, predicted_energy_kwh=3),))
        scenario = dashboard.post("/dashboard/rdn-scenarios", auth=("price-operator", "test-only-password"), json={
            "name": "RDN test", "sourceReference": "operator import",
            "points": [{"intervalStartUtc": run.forecast_origin_utc.isoformat(), "priceUahPerKwh": 7.25}],
        })
        assert scenario.status_code == 201
        scenario_id = scenario.json()["data"]["id"]
        listed = dashboard.get("/dashboard/rdn-scenarios", auth=("price-operator", "test-only-password"))
        assert listed.json()["data"][0]["name"] == "RDN test"
        plan = dashboard.post(f"/dashboard/forecast-runs/{run.run_id}/hourly-plan", auth=("price-operator", "test-only-password"),
            json={"consumptionKwh": [5], "rdnScenarioId": scenario_id})
        assert plan.status_code == 200
        assert plan.json()["data"][0]["estimatedImportCostUah"] == 14.5

def test_bound_device_collection_denies_scope_and_device_mismatch_before_history(db):
    from datetime import date
    from app.deye_device_collection_service import collect_bound_device
    binding=uuid4()
    with psycopg.connect(db) as c:
        c.execute('''INSERT INTO inverter_cloud_binding(binding_id,tenant_id,plant_id,provider,
            external_plant_id,credential_reference,consent_record_reference,mapping_version,
            discovery_status) VALUES (%s,'a','002','deye_cloud','7','server-secret','consent',
            'deye-v1','verified')''',(binding,))
    class Fake:
        auth=0
        def obtain_token(self):self.auth+=1;return 'token'
        def station_devices(self,token,station_ids,*,size):
            assert station_ids==(7,) and size==100
            return {'deviceListItems':[{'deviceSn':'other-device'}]}
        def device_solar_history_for_day(self,*args,**kwargs):pytest.fail('foreign device read')
    api=Fake()
    kwargs=dict(tenant_id='a',plant_id='002',binding_id=binding,device_serial='selected',
        start_day=date(2020,1,1),end_day=date(2020,1,1),client=api)
    with pytest.raises(PermissionError):collect_bound_device(db,'bob',**kwargs)
    assert api.auth==0
    rows=collect_bound_device(db,'alice',**kwargs)
    assert rows[0]['status']=='failed' and rows[0]['errorClass']=='PermissionError'
    with psycopg.connect(db) as c:
        assert c.execute('SELECT count(*) FROM device_solar_capture').fetchone()[0]==0


def test_bound_device_collection_saves_and_skips_without_reauthentication(db):
    from datetime import date
    from app.deye_device_collection_service import collect_bound_device
    binding=uuid4()
    with psycopg.connect(db) as c:
        c.execute('''INSERT INTO inverter_cloud_binding(binding_id,tenant_id,plant_id,provider,
            external_plant_id,credential_reference,consent_record_reference,mapping_version,
            discovery_status) VALUES (%s,'a','002','deye_cloud','7','server-secret','consent',
            'deye-v1','verified')''',(binding,))
    class Fake:
        auth=0;reads=0
        def obtain_token(self):self.auth+=1;return 'token'
        def station_devices(self,token,station_ids,*,size):
            return {'deviceListItems':[{'deviceSn':'selected'}]}
        def device_solar_history_for_day(self,token,serial,*,closed_day_utc):
            self.reads+=1
            origin=int(datetime.combine(closed_day_utc,datetime.min.time(),timezone.utc).timestamp())
            return {'deviceSn':serial,'dataList':[
                {'time':str(origin+i*300),'itemList':[{'key':'TotalSolarPower','unit':'W','value':'1000'}]}
                for i in range(13)]}
    api=Fake()
    kwargs=dict(tenant_id='a',plant_id='002',binding_id=binding,device_serial='selected',
        start_day=date(2020,1,1),end_day=date(2020,1,1),client=api)
    assert collect_bound_device(db,'alice',**kwargs)[0]['status']=='stored'
    assert collect_bound_device(db,'alice',**kwargs)[0]['status']=='already_stored'
    assert (api.auth,api.reads)==(1,1)
    with psycopg.connect(db) as c:
        document=c.execute('SELECT document FROM device_solar_capture').fetchone()[0]
        assert document['scope']=='device_only' and document['hours'][0]['complete']
        assert document['hours'][0]['derivedEnergyKwh']==1
        assert 'selected' not in str(document)
        assert c.execute('SELECT count(*) FROM actual_generation_snapshot').fetchone()[0]==0


@pytest.mark.parametrize('mode',['success','missing_station','failed_auth','missing_devices','wrong_reference','foreign_subject'])
def test_server_deye_binding_verification_commits_only_confirmed_access(db,mode):
    from app.deye_binding_verification import verify_deye_binding
    binding=uuid4()
    with psycopg.connect(db) as c:
        c.execute('''INSERT INTO inverter_cloud_binding(binding_id,tenant_id,plant_id,provider,
            external_plant_id,credential_reference,consent_record_reference,mapping_version)
            VALUES (%s,'a','002','deye_cloud','7','server-ref','consent','deye-v1')''',(binding,))
    class Fake:
        auth=0
        def obtain_token(self):
            self.auth+=1
            if mode=='failed_auth':raise RuntimeError('redacted provider failure')
            return 'token'
        def list_stations(self,token,*,page,size):
            assert (page,size)==(1,100)
            return {'data':{'records':[{'id':8 if mode=='missing_station' else 7,'name':'station'}]}}
        def station_devices(self,token,station_ids,*,size):
            assert station_ids==(7,)
            return {'deviceListItems':[] if mode=='missing_devices' else [{'deviceSn':'private'}]}
    api=Fake()
    kwargs=dict(tenant_id='a',plant_id='002',binding_id=binding,
        credential_reference='wrong' if mode=='wrong_reference' else 'server-ref',client=api)
    if mode=='success':
        assert verify_deye_binding(db,'alice',**kwargs)=={'status':'verified','readOnly':True,'deviceCount':1}
    else:
        with pytest.raises((PermissionError,ValueError,RuntimeError)):
            verify_deye_binding(db,'bob' if mode=='foreign_subject' else 'alice',**kwargs)
    if mode in ('wrong_reference','foreign_subject'):assert api.auth==0
    with psycopg.connect(db) as c:
        assert c.execute('SELECT discovery_status FROM inverter_cloud_binding WHERE binding_id=%s',(binding,)).fetchone()[0]==('verified' if mode=='success' else 'pending')


def test_dashboard_verifies_owned_deye_binding_idempotently_without_client_secrets(db,keys,monkeypatch):
    monkeypatch.setenv('HIOS_DASHBOARD_USER','binding-operator')
    monkeypatch.setenv('HIOS_DASHBOARD_PASSWORD','test-only-password')
    class Fake:
        auth=0
        def obtain_token(self):self.auth+=1;return 'token'
        def list_stations(self,token,*,page,size):return {'data':{'records':[{'id':7,'name':'station'}]}}
        def station_devices(self,token,ids,*,size):return {'deviceListItems':[{'deviceSn':'private'}]}
    api=Fake();monkeypatch.setattr(main_module,'deye_client_from_environment',lambda:api)
    auth=('binding-operator','test-only-password')
    with TestClient(create_app(db,keys[1],'hios-test','hios-api')) as dashboard:
        plant=dashboard.post('/dashboard/plants',auth=auth,json={'name':'Binding pilot'}).json()['data']['id']
        path=f'/dashboard/plants/{plant}/deye-binding/verify'
        body={'stationReference':'7','confirmReadOnly':True}
        assert dashboard.post(path,json=body).status_code==401
        assert dashboard.post(path,auth=auth,json={**body,'appSecret':'forbidden'}).status_code==400
        assert dashboard.post('/dashboard/plants/001/deye-binding/verify',auth=auth,json=body).status_code==403
        assert api.auth==0
        first=dashboard.post(path,auth=auth,json=body)
        assert first.status_code==200 and first.json()['data']['status']=='verified'
        second=dashboard.post(path,auth=auth,json=body)
        assert second.json()['data']['bindingId']==first.json()['data']['bindingId']
        assert 'private' not in first.text
    with psycopg.connect(db) as c:
        assert c.execute('SELECT count(*) FROM inverter_cloud_binding').fetchone()[0]==1


def test_dashboard_failed_deye_verification_leaves_pending_and_redacts_provider(db,keys,monkeypatch):
    from app.deye_openapi import DeyeApiError
    monkeypatch.setenv('HIOS_DASHBOARD_USER','binding-operator')
    monkeypatch.setenv('HIOS_DASHBOARD_PASSWORD','test-only-password')
    class Fake:
        def obtain_token(self):raise DeyeApiError('private-password',provider_code='2101025')
    monkeypatch.setattr(main_module,'deye_client_from_environment',lambda:Fake())
    auth=('binding-operator','test-only-password')
    with TestClient(create_app(db,keys[1],'hios-test','hios-api')) as dashboard:
        plant=dashboard.post('/dashboard/plants',auth=auth,json={'name':'Pending pilot'}).json()['data']['id']
        response=dashboard.post(f'/dashboard/plants/{plant}/deye-binding/verify',auth=auth,
            json={'stationReference':'7','confirmReadOnly':True})
        assert response.status_code==502 and 'private' not in response.text
    with psycopg.connect(db) as c:
        assert c.execute('SELECT discovery_status FROM inverter_cloud_binding').fetchone()[0]=='pending'


def test_dashboard_audits_one_past_deye_day_without_persisting_raw_telemetry(db, keys, monkeypatch):
    monkeypatch.setenv("HIOS_DASHBOARD_USER", "operator")
    monkeypatch.setenv("HIOS_DASHBOARD_PASSWORD", "test-only-password")
    class FakeDeye:
        def obtain_token(self): return "token"
        def station_frame_history_for_day(self, token, station_id, *, closed_day_utc):
            assert (token, station_id, closed_day_utc.isoformat()) == ("token", 7, "2026-09-10")
            return {"stationDataItems": [{"timeStamp": 1_726_000_000, "generationPower": 500,
                                           "generationValue": 1.25}]}
    monkeypatch.setattr(main_module, "deye_client_from_environment", lambda: FakeDeye())
    with TestClient(create_app(db, keys[1], "hios-test", "hios-api")) as dashboard:
        assert dashboard.post("/dashboard/deye/stations/7/telemetry-audit", auth=("operator", "test-only-password"),
                              json={"dateUtc": "2026-09-10"}).status_code == 400
        response = dashboard.post("/dashboard/deye/stations/7/telemetry-audit", auth=("operator", "test-only-password"),
                                  json={"confirmReadOnly": True, "dateUtc": "2026-09-10"})
        assert response.status_code == 200
        assert response.json()["data"]["persistence"] == "not_written"
        assert response.json()["data"]["sample_count"] == 1
