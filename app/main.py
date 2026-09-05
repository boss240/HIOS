"""HIOS Sprint 1 API. Configuration is mandatory; no insecure defaults."""
import os
from pathlib import Path
from uuid import uuid4

import jwt
import psycopg
import yaml
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

ROOT = Path(__file__).resolve().parents[1]


def create_app(database_url=None, public_key=None, issuer=None, audience=None):
    database_url = database_url or os.environ["DATABASE_URL"]
    public_key = public_key or Path(os.environ["JWT_PUBLIC_KEY_FILE"]).read_text()
    issuer = issuer or os.environ["JWT_ISSUER"]
    audience = audience or os.environ["JWT_AUDIENCE"]
    key = load_pem_public_key(public_key.encode())
    if not isinstance(key, RSAPublicKey) or key.key_size < 2048:
        raise ValueError("An RSA public key of at least 2048 bits is required")
    if not issuer.strip() or not audience.strip():
        raise ValueError("Issuer and audience must not be empty")
    api = FastAPI(title="HIOS API", docs_url=None, redoc_url=None)
    api.openapi = lambda: yaml.safe_load((ROOT / "docs/api/openapi.yaml").read_text())

    def error(request, status, code, message):
        headers = {"WWW-Authenticate": "Bearer"} if status == 401 else {}
        return JSONResponse(
            {"error": {"code": code, "message": message,
                       "requestId": request.state.request_id}},
            status_code=status, headers=headers,
        )

    @api.middleware("http")
    async def request_context(request, call_next):
        request.state.request_id = str(uuid4())
        try:
            response = await call_next(request)
        except Exception:
            # Do not expose DB failures, tokens or stack traces.
            response = error(request, 500, "INTERNAL_ERROR", "Internal error")
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @api.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        codes = {400: "VALIDATION_ERROR", 401: "AUTH_REQUIRED",
                 403: "ACCESS_DENIED", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}
        messages = {400: "Invalid pagination parameters", 401: "Authentication required",
                    403: "Access denied", 404: "Resource not found", 405: "Method not allowed"}
        return error(request, exc.status_code, codes.get(exc.status_code, "INTERNAL_ERROR"),
                     messages.get(exc.status_code, "Internal error"))

    @api.get("/health")
    def health():
        return {"status": "ok"}

    @api.get("/plants")
    def plants(request: Request):
        authorization = request.headers.get("Authorization", "").split()
        if len(authorization) != 2 or authorization[0].lower() != "bearer":
            raise HTTPException(401)
        try:
            claims = jwt.decode(
                authorization[1], public_key, algorithms=["RS256"],
                issuer=issuer, audience=audience,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
            if not isinstance(claims["sub"], str) or not claims["sub"].strip():
                raise jwt.InvalidTokenError()
        except jwt.InvalidTokenError:
            raise HTTPException(401)
        tenant = claims.get("tenant_id")
        if not isinstance(tenant, str) or not tenant.strip():
            raise HTTPException(403)
        # Tenant headers/query values cannot override the signed tenant claim.
        paging = {}
        for name, default, maximum in [("limit", 50, 100), ("offset", 0, 2147483647)]:
            values = request.query_params.getlist(name)
            value = values[0] if values else str(default)
            if len(values) > 1 or not value.isascii() or not value.isdecimal() or len(value) > 10:
                raise HTTPException(400)
            number = int(value)
            if number < (1 if name == "limit" else 0) or number > maximum:
                raise HTTPException(400)
            paging[name] = number
        with psycopg.connect(database_url, connect_timeout=5) as connection:
            # A single statement takes one snapshot for membership and plant access.
            row = connection.execute(
                """WITH allowed AS (
                    SELECT 1 FROM membership WHERE tenant_id = %s AND subject = %s AND active
                ), page AS (
                    SELECT public_id, name, capacity_kw FROM plant
                    WHERE tenant_id = %s AND EXISTS (SELECT 1 FROM allowed)
                    ORDER BY public_id COLLATE "C" LIMIT %s OFFSET %s
                )
                SELECT EXISTS (SELECT 1 FROM allowed),
                       COALESCE((SELECT json_agg(json_build_object(
                         'id', public_id, 'name', name, 'capacityKw', capacity_kw)
                         ORDER BY public_id COLLATE "C") FROM page), '[]'::json)""",
                (tenant, claims["sub"], tenant, paging["limit"], paging["offset"]),
            ).fetchone()
        if not row[0]:
            raise HTTPException(403)
        data = [{k: v for k, v in plant.items() if v is not None} for plant in row[1]]
        return {"data": data, **paging}

    return api
