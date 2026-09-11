"""Constrained Deye OpenAPI v1 reader for the approved pilot.

This module never schedules work, discovers credentials, writes to Deye, or
contains a control endpoint. Callers must inject short-lived credentials from a
secret manager and explicitly invoke an individual read operation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Mapping

import httpx


EU_BASE_URL = "https://eu1-developer.deyecloud.com"
_READ_PATHS = frozenset({
    "/v1.0/account/info", "/v1.0/account/token", "/v1.0/station/list",
    "/v1.0/station/device", "/v1.0/station/history", "/v1.0/station/history/power",
    "/v1.0/station/latest", "/v1.0/station/alertList",
})


class DeyeApiError(RuntimeError):
    """A redacted Deye API failure; response bodies and credentials are excluded."""

    def __init__(self, message: str, *, endpoint: str | None = None,
                 status_code: int | None = None, provider_code: str | int | None = None) -> None:
        super().__init__(message)
        self.endpoint = endpoint
        self.status_code = status_code
        self.provider_code = provider_code


@dataclass(frozen=True)
class DeyeCredentials:
    app_id: str = field(repr=False)
    app_secret: str = field(repr=False)
    email: str = field(repr=False)
    password: str = field(repr=False)
    company_id: int = 0

    def __post_init__(self) -> None:
        if any(not isinstance(value, str) or not value.strip()
               for value in (self.app_id, self.app_secret, self.email, self.password)):
            raise ValueError("Deye credentials must be non-empty")
        if not isinstance(self.company_id, int) or self.company_id < 0:
            raise ValueError("company_id must be a non-negative integer")


class DeyeReadOnlyClient:
    """Small synchronous client with a fixed endpoint allowlist and no retries."""

    def __init__(self, credentials: DeyeCredentials, *, http: httpx.Client | None = None,
                 base_url: str = EU_BASE_URL) -> None:
        if not base_url.startswith("https://"):
            raise ValueError("Deye base URL must use HTTPS")
        self._credentials = credentials
        self._http = http or httpx.Client(base_url=base_url, timeout=15.0)
        self._base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: dict[str, Any], *, token: str | None = None,
              params: Mapping[str, str] | None = None) -> dict[str, Any]:
        if path not in _READ_PATHS:
            raise DeyeApiError("Deye endpoint is not approved for read-only use", endpoint=path)
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = token if token.casefold().startswith("bearer ") else f"bearer {token}"
        try:
            response = self._http.post(self._base_url + path, headers=headers, json=payload,
                                       params=params)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as error:
            status_code = error.response.status_code if isinstance(error, httpx.HTTPStatusError) else None
            raise DeyeApiError("Deye read request failed", endpoint=path, status_code=status_code) from error
        if not isinstance(body, dict) or body.get("success") is False:
            raise DeyeApiError("Deye rejected the read request", endpoint=path,
                               status_code=response.status_code,
                               provider_code=body.get("code") if isinstance(body, dict) else None)
        return body

    def obtain_token(self) -> str:
        digest = sha256(self._credentials.password.encode("utf-8")).hexdigest()
        body = self._post("/v1.0/account/token", {
            "appSecret": self._credentials.app_secret, "email": self._credentials.email,
            "companyId": str(self._credentials.company_id), "password": digest,
        }, params={"appId": self._credentials.app_id})
        token = body.get("accessToken")
        if not isinstance(token, str) or not token.strip():
            raise DeyeApiError("Deye token response was incomplete")
        return token

    def list_stations(self, token: str, *, page: int = 1, size: int = 50) -> dict[str, Any]:
        if page < 1 or not 1 <= size <= 100:
            raise ValueError("page must be positive and size must be 1..100")
        return self._post("/v1.0/station/list", {"page": page, "size": size}, token=token)

    def station_devices(self, token: str, station_ids: tuple[int, ...], *,
                        page: int = 1, size: int = 20) -> dict[str, Any]:
        """Read devices for the one or two explicitly selected pilot stations."""
        if page < 1 or not 1 <= size <= 100:
            raise ValueError("page must be positive and size must be 1..100")
        if not 1 <= len(station_ids) <= 2 or any(
                isinstance(station_id, bool) or not isinstance(station_id, int) or station_id <= 0
                for station_id in station_ids):
            raise ValueError("station_ids must contain one or two positive integer pilot IDs")
        return self._post("/v1.0/station/device", {
            "page": page, "size": size, "stationIds": list(station_ids),
        }, token=token)

    def station_history(self, token: str, station_id: int, *, granularity: int,
                        start_at: str, end_at: str | None = None) -> dict[str, Any]:
        if station_id <= 0 or granularity not in {1, 2, 3, 4} or not start_at:
            raise ValueError("station history arguments are invalid")
        payload: dict[str, Any] = {"stationId": station_id, "granularity": granularity, "startAt": start_at}
        if end_at:
            payload["endAt"] = end_at
        return self._post("/v1.0/station/history", payload, token=token)
