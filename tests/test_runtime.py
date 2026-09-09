import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import jwt
import psycopg
import pytest
import yaml
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

SPEC = yaml.safe_load(Path("docs/api/openapi.yaml").read_text())


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
        assert connection.execute("SELECT count(*) FROM schema_migration").fetchone()[0] == 6
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
