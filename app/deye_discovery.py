"""Explicit, read-only discovery of Deye stations for the dashboard operator."""
from __future__ import annotations

import os
from collections.abc import Mapping

from app.deye_openapi import DeyeCredentials, DeyeReadOnlyClient
from app.deye_station_discovery import DeyeStationCandidate, station_candidates


def client_from_environment(environment: Mapping[str, str] | None = None) -> DeyeReadOnlyClient:
    """Build a read-only client from server-side configuration only."""
    values = environment if environment is not None else os.environ
    required = ("DEYE_APP_ID", "DEYE_APP_SECRET", "DEYE_ACCOUNT_EMAIL", "DEYE_ACCOUNT_PASSWORD")
    if any(not values.get(name, "").strip() for name in required):
        raise ValueError("Deye discovery is not configured")
    try:
        company_id = int(values.get("DEYE_COMPANY_ID", "0"))
    except ValueError as error:
        raise ValueError("Deye discovery is not configured") from error
    return DeyeReadOnlyClient(DeyeCredentials(
        values["DEYE_APP_ID"], values["DEYE_APP_SECRET"], values["DEYE_ACCOUNT_EMAIL"],
        values["DEYE_ACCOUNT_PASSWORD"], company_id,
    ))


def discover_stations(client: DeyeReadOnlyClient) -> tuple[DeyeStationCandidate, ...]:
    """Read one bounded station page; no station is persisted or modified."""
    return station_candidates(client.list_stations(client.obtain_token(), page=1, size=100))
