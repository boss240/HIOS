import os
import time
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
        assert connection.execute("SELECT count(*) FROM schema_migration").fetchone()[0] == 1
    for value in [-1, float("inf"), float("nan")]:
        with pytest.raises(psycopg.errors.CheckViolation):
            with psycopg.connect(db) as connection:
                connection.execute("INSERT INTO plant VALUES ('bad','a','Bad',%s)", (value,))


def test_database_failure_is_safe_and_health_independent(keys):
    with TestClient(create_app("postgresql://invalid:invalid@127.0.0.1:1/missing",
                               keys[1], "hios-test", "hios-api")) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/plants", headers=headers(keys))
        assert response.status_code == 500
        contract(response, "/plants")
        assert response.json()["error"]["message"] == "Internal error"
