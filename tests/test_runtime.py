import os
import time
from datetime import datetime
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
from app.forecast_store import ForecastRun, create_or_get_run

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
        assert connection.execute("SELECT count(*) FROM schema_migration").fetchone()[0] == 2
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
