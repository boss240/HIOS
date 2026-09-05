# Run the Sprint 1 API

Related: #7, #8, #19; [ADR-0001](../architecture/adr/0001-sprint-1-runtime.md).

## Configuration

Python 3.11 and PostgreSQL 17 are required. Install requirements-runtime.txt in a
virtual environment. Supply configuration through the process environment:

- DATABASE_URL: PostgreSQL connection string; migration runner uses DDL credentials,
  API uses a separate SELECT-only role for tenant, membership and plant.
- JWT_PUBLIC_KEY_FILE: path outside the repository to the trusted RSA public PEM.
- JWT_ISSUER: exact trusted issuer string.
- JWT_AUDIENCE: expected API audience.

No default credentials or signing keys are installed. The API does not issue
tokens. Configure the existing identity system to sign RS256 tokens with sub,
tenant_id, iss, aud, iat and exp. Provision tenant/membership/plant records through
controlled database administration; there is no public administrative write API.

## Commands

Run from the repository root:

```sh
python -m pip install -r requirements-runtime.txt
python -m app.migrate
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Run migrations with migration credentials first; switch DATABASE_URL to runtime
credentials before starting Uvicorn. Grant runtime CONNECT on its database,
USAGE on the application schema, and SELECT on tenant, membership and plant.
Do not grant runtime CREATE, INSERT, UPDATE or DELETE.

GET /health is public liveness. GET /plants requires a trusted bearer token and
active membership. It accepts limit 1–100 (default 50), offset 0–2147483647
(default 0), and returns data, limit, offset ordered by public ID using C collation.
Missing capacity is omitted. Invalid paging returns 400; failed identity 401;
forbidden tenant 403; database failure a safe 500. X-Request-ID is server-generated.

OpenAPI is served at /openapi.json from the canonical repository contract.
TLS termination and production provisioning are outside this Sprint 1 local/CI slice.

## Integration evidence

Set TEST_DATABASE_URL to a dedicated PostgreSQL test database and install
requirements-test.txt, then run:

```sh
python -m pytest -q --junitxml=test-results.xml
```

Tests create uniquely named schemas and remove only those schemas afterwards.
The test role needs schema creation rights. Never point tests at production.
GitHub Actions provisions PostgreSQL 17 and uploads the JUnit result artifact.
Tests use real database queries, in-process ASGI requests and an ephemeral
Uvicorn TCP HTTP server. This is not an externally deployed production service.

Sources: [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/),
[PyJWT validation](https://pyjwt.readthedocs.io/en/latest/api.html).
