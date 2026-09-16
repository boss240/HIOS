"""HIOS Sprint 1 API. Configuration is mandatory; no insecure defaults."""
import base64
import hmac
import os
from pathlib import Path
from datetime import date
from uuid import UUID, uuid4

import jwt
import psycopg
import yaml
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from fastapi import FastAPI, Request, HTTPException, Body
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.inverter_cloud import InverterCloudBinding, InverterCloudProvider
from app.deye_station_reference import station_id_from_reference
from app.deye_discovery import client_from_environment as deye_client_from_environment, discover_stations
from app.deye_openapi import DeyeApiError
from app.plant_onboarding import PlantProfileInput, add_read_only_binding, create_plant, delete_plant, get_onboarding
from app.weather_provider_registry import PROVIDER_CATALOG, configure_channel, list_channels
from app.inverter_connection_request import list_connection_requests, request_connection

ROOT = Path(__file__).resolve().parents[1]


def create_app(database_url=None, public_key=None, issuer=None, audience=None):
    database_url = database_url or os.environ["DATABASE_URL"]
    if public_key is None:
        # Azure Container Apps stores configuration as environment variables;
        # a mounted key file remains supported for local and existing deployments.
        public_key = os.environ.get("JWT_PUBLIC_KEY")
        if public_key is None:
            public_key = Path(os.environ["JWT_PUBLIC_KEY_FILE"]).read_text()
    issuer = issuer or os.environ["JWT_ISSUER"]
    audience = audience or os.environ["JWT_AUDIENCE"]
    key = load_pem_public_key(public_key.encode())
    if not isinstance(key, RSAPublicKey) or key.key_size < 2048:
        raise ValueError("An RSA public key of at least 2048 bits is required")
    if not issuer.strip() or not audience.strip():
        raise ValueError("Issuer and audience must not be empty")
    api = FastAPI(title="HIOS API", docs_url=None, redoc_url=None)
    api.openapi = lambda: yaml.safe_load((ROOT / "docs/api/openapi.yaml").read_text())
    api.mount("/assets", StaticFiles(directory=str(ROOT / "web")), name="assets")
    dashboard_user = os.environ.get("HIOS_DASHBOARD_USER", "")
    dashboard_password = os.environ.get("HIOS_DASHBOARD_PASSWORD", "")
    if bool(dashboard_user) != bool(dashboard_password):
        raise ValueError("HIOS_DASHBOARD_USER and HIOS_DASHBOARD_PASSWORD must be set together")

    def dashboard_authorized(request: Request) -> bool:
        if not dashboard_user:
            return True
        scheme, _, encoded = request.headers.get("Authorization", "").partition(" ")
        if scheme.lower() != "basic" or not encoded:
            return False
        try:
            supplied = base64.b64decode(encoded, validate=True).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return False
        # compare_digest() only accepts ASCII str inputs. Basic Auth is UTF-8,
        # so compare the encoded values to support non-ASCII dashboard secrets.
        expected = f"{dashboard_user}:{dashboard_password}"
        return hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8"))

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
        if request.url.path == "/" or request.url.path.startswith("/assets/"):
            if not dashboard_authorized(request):
                response = JSONResponse(
                    {"error": {"code": "AUTH_REQUIRED", "message": "Dashboard authentication required",
                               "requestId": request.state.request_id}},
                    status_code=401,
                    headers={"WWW-Authenticate": 'Basic realm="HIOS Forecast"'},
                )
                response.headers["X-Request-ID"] = request.state.request_id
                return response
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

    def authenticated_context(request: Request) -> tuple[str, str]:
        authorization = request.headers.get("Authorization", "").split()
        if len(authorization) != 2 or authorization[0].lower() != "bearer":
            raise HTTPException(401)
        try:
            claims = jwt.decode(
                authorization[1], public_key, algorithms=["RS256"], issuer=issuer, audience=audience,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
            if not isinstance(claims["sub"], str) or not claims["sub"].strip():
                raise jwt.InvalidTokenError()
        except jwt.InvalidTokenError:
            raise HTTPException(401)
        tenant = claims.get("tenant_id")
        if not isinstance(tenant, str) or not tenant.strip():
            raise HTTPException(403)
        return tenant, claims["sub"]

    def paging(request: Request) -> dict[str, int]:
        result = {}
        for name, default, maximum in [("limit", 50, 100), ("offset", 0, 2147483647)]:
            values = request.query_params.getlist(name)
            value = values[0] if values else str(default)
            if len(values) > 1 or not value.isascii() or not value.isdecimal() or len(value) > 10:
                raise HTTPException(400)
            number = int(value)
            if number < (1 if name == "limit" else 0) or number > maximum:
                raise HTTPException(400)
            result[name] = number
        return result

    @api.get("/", include_in_schema=False)
    def forecast_dashboard():
        """Serve the credentials-free HIOS Forecast commercial prototype."""
        return FileResponse(ROOT / "web" / "index.html")

    @api.get("/health")
    def health():
        return {"status": "ok"}

    @api.get("/plants")
    def plants(request: Request):
        tenant, subject = authenticated_context(request)
        # Tenant headers/query values cannot override the signed tenant claim.
        page = paging(request)
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
                (tenant, subject, tenant, page["limit"], page["offset"]),
            ).fetchone()
        if not row[0]:
            raise HTTPException(403)
        data = [{k: v for k, v in plant.items() if v is not None} for plant in row[1]]
        return {"data": data, **page}

    def onboarding_profile(body: dict) -> PlantProfileInput:
        fields = {
            "latitude": body.get("latitude"), "longitude": body.get("longitude"),
            "timezone_name": body.get("timezone"), "capacity_ac_kw": body.get("capacityAcKw"),
            "tilt_deg": body.get("tiltDeg"), "azimuth_deg": body.get("azimuthDeg"),
            "mounting_type": body.get("mountingType"), "meter_boundary": body.get("meterBoundary"),
            "operator_notes": body.get("operatorNotes"),
        }
        commissioned = body.get("commissioningDate")
        if commissioned is not None:
            if not isinstance(commissioned, str):
                raise ValueError("commissioningDate must be ISO date")
            fields["commissioning_date"] = date.fromisoformat(commissioned)
        return PlantProfileInput(**fields)

    @api.post("/plants", status_code=201)
    def register_plant(request: Request, body: dict = Body(...)):
        tenant, subject = authenticated_context(request)
        try:
            plant_id = create_plant(database_url=database_url, subject=subject, tenant_id=tenant,
                name=body.get("name"), capacity_kw=body.get("capacityKw"), profile=onboarding_profile(body))
        except (TypeError, ValueError):
            raise HTTPException(400)
        return {"data": {"id": plant_id}}

    @api.get("/plants/{plant_id}/onboarding")
    def plant_onboarding(request: Request, plant_id: str):
        tenant, subject = authenticated_context(request)
        try:
            return {"data": get_onboarding(database_url=database_url, subject=subject,
                                              tenant_id=tenant, plant_id=plant_id)}
        except PermissionError:
            raise HTTPException(404)

    @api.post("/plants/{plant_id}/cloud-bindings", status_code=201)
    def register_cloud_binding(request: Request, plant_id: str, body: dict = Body(...)):
        tenant, subject = authenticated_context(request)
        try:
            binding = InverterCloudBinding(
                tenant_id=tenant, plant_id=plant_id,
                provider=InverterCloudProvider(body.get("provider")),
                external_plant_id=body.get("externalPlantId"),
                credential_reference=body.get("credentialReference"),
                consent_record_reference=body.get("consentRecordReference"),
                mapping_version=body.get("mappingVersion"),
            )
            binding_id = add_read_only_binding(database_url=database_url, subject=subject, binding=binding,
                                               discovery_status=body.get("discoveryStatus", "pending"))
        except (TypeError, ValueError):
            raise HTTPException(400)
        except PermissionError:
            raise HTTPException(404)
        return {"data": {"id": str(binding_id), "readOnly": True}}

    def dashboard_context(request: Request) -> tuple[str, str]:
        """Resolve the one dashboard operator to an isolated tenant, after Basic authentication."""
        if not dashboard_user or not dashboard_authorized(request):
            raise HTTPException(401)
        tenant = "dashboard-" + __import__("hashlib").sha256(dashboard_user.encode("utf-8")).hexdigest()[:24]
        with psycopg.connect(database_url, connect_timeout=5) as connection:
            connection.execute("INSERT INTO tenant(id) VALUES (%s) ON CONFLICT DO NOTHING", (tenant,))
            connection.execute("""INSERT INTO membership(tenant_id,subject,active) VALUES (%s,%s,true)
                                ON CONFLICT (tenant_id,subject) DO NOTHING""", (tenant, dashboard_user))
        return tenant, dashboard_user

    @api.post("/dashboard/plants/register-by-provider-id", status_code=201, include_in_schema=False)
    def dashboard_register_by_provider_id(request: Request, body: dict = Body(...)):
        tenant, subject = dashboard_context(request)
        try:
            provider = InverterCloudProvider(body.get("provider"))
            external_id = body.get("externalPlantId")
            if provider is InverterCloudProvider.DEYE_CLOUD:
                external_id = station_id_from_reference(external_id)
            elif not isinstance(external_id, str) or not external_id.strip():
                raise ValueError("externalPlantId is required")
            plant_id = create_plant(database_url=database_url, subject=subject, tenant_id=tenant,
                name=f"{provider.value.replace('_', ' ').title()} · {external_id.strip()}",
                capacity_kw=None, profile=PlantProfileInput())
            item = request_connection(database_url=database_url, tenant_id=tenant, subject=subject,
                                      plant_id=plant_id, provider=provider, external_plant_id=external_id)
        except (TypeError, ValueError):
            raise HTTPException(400)
        return {"data": {"plantId": plant_id, "requestId": str(item.request_id), "status": item.status}}

    @api.post("/dashboard/deye/stations/discover", include_in_schema=False)
    def dashboard_discover_deye_stations(request: Request, body: dict = Body(...)):
        """Return Deye stations only after an explicit read-only operator action."""
        dashboard_context(request)
        if body.get("confirmReadOnly") is not True:
            raise HTTPException(400)
        try:
            candidates = discover_stations(deye_client_from_environment())
        except ValueError:
            raise HTTPException(503, detail="Deye discovery is not configured")
        except DeyeApiError:
            raise HTTPException(502, detail="Deye discovery could not be completed")
        return {"data": [{"id": str(item.station_id), "name": item.name} for item in candidates]}
    @api.get("/dashboard/plants", include_in_schema=False)
    def dashboard_plants(request: Request):
        tenant, subject = dashboard_context(request)
        with psycopg.connect(database_url, connect_timeout=5) as connection:
            rows = connection.execute(
                "SELECT public_id,name,capacity_kw FROM plant WHERE tenant_id=%s ORDER BY created_at DESC",
                (tenant,),
            ).fetchall()
        return {"data": [{"id": row[0], "name": row[1], "capacityKw": row[2]} for row in rows]}

    @api.post("/dashboard/plants", status_code=201, include_in_schema=False)
    def dashboard_register_plant(request: Request, body: dict = Body(...)):
        tenant, subject = dashboard_context(request)
        try:
            plant_id = create_plant(database_url=database_url, subject=subject, tenant_id=tenant,
                name=body.get("name"), capacity_kw=body.get("capacityKw"), profile=onboarding_profile(body))
        except (TypeError, ValueError):
            raise HTTPException(400)
        return {"data": {"id": plant_id}}

    @api.delete("/dashboard/plants/{plant_id}", status_code=204, include_in_schema=False)
    def dashboard_delete_plant(request: Request, plant_id: str, body: dict = Body(...)):
        tenant, subject = dashboard_context(request)
        try:
            delete_plant(database_url=database_url, subject=subject, tenant_id=tenant, plant_id=plant_id,
                         confirmation_name=body.get("confirmationName"))
        except ValueError:
            raise HTTPException(400)
        except PermissionError:
            raise HTTPException(404)
    @api.get("/dashboard/plants/{plant_id}/cloud-requests", include_in_schema=False)
    def dashboard_cloud_requests(request: Request, plant_id: str):
        tenant, subject = dashboard_context(request)
        try:
            requests = list_connection_requests(database_url=database_url, tenant_id=tenant,
                                                subject=subject, plant_id=plant_id)
        except PermissionError:
            raise HTTPException(404)
        return {"data": [{"id": str(item.request_id), "provider": item.provider, "status": item.status}
                         for item in requests]}

    @api.post("/dashboard/plants/{plant_id}/cloud-requests", status_code=201, include_in_schema=False)
    def dashboard_cloud_request(request: Request, plant_id: str, body: dict = Body(...)):
        tenant, subject = dashboard_context(request)
        try:
            item = request_connection(database_url=database_url, tenant_id=tenant, subject=subject,
                                      plant_id=plant_id, provider=InverterCloudProvider(body.get("provider")))
        except ValueError:
            raise HTTPException(400)
        except PermissionError:
            raise HTTPException(404)
        return {"data": {"id": str(item.request_id), "provider": item.provider, "status": item.status}}
    @api.get("/dashboard/weather-providers", include_in_schema=False)
    def dashboard_weather_providers(request: Request):
        tenant, subject = dashboard_context(request)
        channels = list_channels(database_url=database_url, tenant_id=tenant, subject=subject)
        return {"data": [
            {"id": channel.provider, "name": PROVIDER_CATALOG[channel.provider].name,
             "detail": PROVIDER_CATALOG[channel.provider].summary, "category": PROVIDER_CATALOG[channel.provider].category,
             "role": channel.role, "status": channel.status}
            for channel in channels
        ]}

    @api.post("/dashboard/weather-providers", status_code=201, include_in_schema=False)
    def dashboard_weather_provider(request: Request, body: dict = Body(...)):
        tenant, subject = dashboard_context(request)
        try:
            channel = configure_channel(database_url=database_url, tenant_id=tenant, subject=subject,
                provider=body.get("provider"), role=body.get("role"), status="candidate")
        except ValueError:
            raise HTTPException(400)
        return {"data": {"id": channel.provider, "role": channel.role, "status": channel.status}}
    @api.get("/forecast-runs/{run_id}")
    def forecast_run(request: Request, run_id: str):
        """Return one authorized immutable forecast run and a bounded point page."""
        tenant, subject = authenticated_context(request)
        page = paging(request)
        try:
            run_uuid = UUID(run_id)
        except ValueError:
            raise HTTPException(400)
        with psycopg.connect(database_url, connect_timeout=5) as connection:
            row = connection.execute(
                """WITH allowed AS (
                    SELECT 1 FROM membership WHERE tenant_id=%s AND subject=%s AND active
                ), owned_run AS (
                    SELECT r.* FROM forecast_run r
                    WHERE r.run_id=%s AND r.tenant_id=%s AND EXISTS (SELECT 1 FROM allowed)
                ), page AS (
                    SELECT p.interval_start_utc, p.interval_end_utc, p.predicted_power_kw,
                           p.predicted_energy_kwh, p.quality_flags, p.provider_provenance
                    FROM forecast_point p JOIN owned_run r ON r.run_id=p.run_id
                    ORDER BY p.interval_start_utc ASC LIMIT %s OFFSET %s
                ) SELECT EXISTS (SELECT 1 FROM allowed),
                    (SELECT json_build_object(
                        'id', r.run_id, 'plantId', r.plant_id,
                        'forecastOriginUtc', r.forecast_origin_utc, 'horizonId', r.horizon_id,
                        'modelId', r.model_id, 'modelVersion', r.model_version,
                        'featureVersion', r.feature_version, 'status', r.status,
                        'points', COALESCE((SELECT json_agg(json_build_object(
                            'intervalStartUtc', interval_start_utc, 'intervalEndUtc', interval_end_utc,
                            'predictedPowerKw', predicted_power_kw, 'predictedEnergyKwh', predicted_energy_kwh,
                            'qualityFlags', quality_flags, 'providerProvenance', provider_provenance
                        ) ORDER BY interval_start_utc) FROM page), '[]'::json)
                    ) FROM owned_run r)""",
                (tenant, subject, run_uuid, tenant, page["limit"], page["offset"]),
            ).fetchone()
        if not row[0]:
            raise HTTPException(403)
        if row[1] is None:
            raise HTTPException(404)
        return {"data": row[1], **page}

    @api.get("/plants/{plant_id}/forecast-runs")
    def plant_forecast_runs(request: Request, plant_id: str):
        """Return a bounded newest-first list of immutable runs for one owned plant."""
        tenant, subject = authenticated_context(request)
        page = paging(request)
        with psycopg.connect(database_url, connect_timeout=5) as connection:
            row = connection.execute(
                """WITH allowed AS (
                    SELECT 1 FROM membership WHERE tenant_id=%s AND subject=%s AND active
                ), owned_plant AS (
                    SELECT 1 FROM plant WHERE tenant_id=%s AND public_id=%s
                      AND EXISTS (SELECT 1 FROM allowed)
                ), page AS (
                    SELECT r.run_id, r.forecast_origin_utc, r.horizon_id, r.model_id,
                           r.model_version, r.feature_version, r.status,
                           (SELECT count(*) FROM forecast_point p WHERE p.run_id=r.run_id) AS point_count
                    FROM forecast_run r WHERE r.tenant_id=%s AND r.plant_id=%s
                      AND EXISTS (SELECT 1 FROM owned_plant)
                    ORDER BY r.forecast_origin_utc DESC, r.run_id DESC LIMIT %s OFFSET %s
                ) SELECT EXISTS (SELECT 1 FROM allowed), EXISTS (SELECT 1 FROM owned_plant),
                    COALESCE((SELECT json_agg(json_build_object(
                        'id', run_id, 'forecastOriginUtc', forecast_origin_utc, 'horizonId', horizon_id,
                        'modelId', model_id, 'modelVersion', model_version,
                        'featureVersion', feature_version, 'status', status, 'pointCount', point_count
                    ) ORDER BY forecast_origin_utc DESC, run_id DESC) FROM page), '[]'::json)""",
                (tenant, subject, tenant, plant_id, tenant, plant_id, page["limit"], page["offset"]),
            ).fetchone()
        if not row[0]:
            raise HTTPException(403)
        if not row[1]:
            raise HTTPException(404)
        return {"data": row[2], **page}

    return api
