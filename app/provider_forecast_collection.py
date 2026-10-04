"""One explicitly invoked source forecast retrieval and tenant-scoped capture."""
from datetime import datetime, timezone
import os
from uuid import uuid4
import psycopg
from app.provider_forecast_capture import store_forecast_capture
from app.weather_provider_clients import GoogleWeatherReadClient, SolcastReadClient
from app.weather_provider_credentials import ProviderApiKey
from app.weather_provider_requests import GoogleHourlyForecastRequest, SolcastRadiationForecastRequest
from app.weather_provider_roles import WeatherProvider


def collect_provider_forecast(database_url: str, subject: str, *, tenant_id: str,
                              plant_id: str, provider: str, environment=None,
                              reader=None, clock=None) -> dict:
    """Read one source for an owned plant and freeze future complete intervals.

    No retries, scheduler, inverter operations or composed forecast publication.
    The receipt clock is sampled after the provider response has been parsed.
    """
    if not isinstance(provider,str) or provider not in {'google_weather','solcast'}:
        raise ValueError('collection supports Google Weather and Solcast')
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        coordinates = connection.execute('''SELECT pp.latitude,pp.longitude
            FROM plant p JOIN membership m ON m.tenant_id=p.tenant_id
            LEFT JOIN plant_profile pp ON pp.plant_id=p.public_id
            WHERE p.tenant_id=%s AND p.public_id=%s AND m.subject=%s AND m.active''',
            (tenant_id,plant_id,subject)).fetchone()
    if coordinates is None:
        raise PermissionError('active membership and tenant-owned plant required')
    latitude, longitude = coordinates
    if latitude is None or longitude is None:
        raise ValueError('plant coordinates are required before weather collection')
    if reader is None:
        env = os.environ if environment is None else environment
        name = 'GOOGLE_WEATHER_API_KEY' if provider == 'google_weather' else 'SOLCAST_API_KEY'
        key = ProviderApiKey(WeatherProvider(provider), env.get(name,''))
        reader = GoogleWeatherReadClient(key) if provider == 'google_weather' else SolcastReadClient(key)
    if provider == 'google_weather':
        rows = reader.hourly_forecast(GoogleHourlyForecastRequest(latitude,longitude,hours=24,page_size=24))
        version = 'google-hourly-v1'
    else:
        rows = reader.radiation_forecast(SolcastRadiationForecastRequest(latitude,longitude))
        version = 'solcast-radiation-v1'
    captured = (clock or (lambda: datetime.now(timezone.utc)))()
    # Discard already-started intervals explicitly; never backdate receipt.
    future = tuple(row for row in rows if row.valid_at_utc > captured)
    if not future:
        raise ValueError('provider returned no complete future intervals')
    capture_id = store_forecast_capture(database_url,subject,capture_id=uuid4(),
        tenant_id=tenant_id,plant_id=plant_id,provider=provider,mapping_version=version,
        captured_at=captured,intervals=future)
    return {'captureId':str(capture_id),'provider':provider,
            'capturedAtUtc':captured.isoformat(),'intervalCount':len(future),
            'excludedStartedIntervals':len(rows)-len(future),'providerIssuedAtUtc':None}


def list_provider_captures(database_url: str, subject: str, *, tenant_id: str,
                           plant_id: str) -> list[dict]:
    """Return at most 100 capture summaries, with membership verified in one read."""
    with psycopg.connect(database_url,connect_timeout=5) as connection:
        allowed = connection.execute('''SELECT 1 FROM plant p JOIN membership m
            ON m.tenant_id=p.tenant_id WHERE p.tenant_id=%s AND p.public_id=%s
            AND m.subject=%s AND m.active''',(tenant_id,plant_id,subject)).fetchone()
        if allowed is None:
            raise PermissionError('active membership and tenant-owned plant required')
        rows = connection.execute('''SELECT c.capture_id,c.provider,c.captured_at_utc,
            c.provider_issued_at_utc,jsonb_array_length(c.document->'intervals')
            FROM provider_forecast_capture c WHERE c.tenant_id=%s AND c.plant_id=%s
            AND EXISTS (SELECT 1 FROM membership m WHERE m.tenant_id=c.tenant_id
                AND m.subject=%s AND m.active)
            ORDER BY c.captured_at_utc DESC LIMIT 100''',(tenant_id,plant_id,subject)).fetchall()
    return [{'captureId':str(r[0]),'provider':r[1],'capturedAtUtc':r[2].isoformat(),
             'providerIssuedAtUtc':None if r[3] is None else r[3].isoformat(),
             'intervalCount':r[4]} for r in rows]
