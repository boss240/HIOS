"""Manually discover only the two approved Deye pilot station IDs."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.deye_openapi import DeyeApiError, DeyeCredentials, DeyeReadOnlyClient

PILOTS_BY_NAME_PREFIX = {
    "Погреби": "deye-pilot-pohreby",
    "Борщів": "deye-pilot-borshchiv",
}

def credentials_from_environment(environment: dict[str, str] | None = None) -> DeyeCredentials:
    values = environment if environment is not None else os.environ
    required = (
        "DEYE_APP_ID",
        "DEYE_APP_SECRET",
        "DEYE_ACCOUNT_EMAIL",
        "DEYE_ACCOUNT_PASSWORD",
    )
    missing = [name for name in required if not values.get(name, "").strip()]
    if missing:
        raise ValueError("missing Deye environment variables: " + ", ".join(missing))

    try:
        company_id = int(values.get("DEYE_COMPANY_ID", "0"))
    except ValueError as error:
        raise ValueError("DEYE_COMPANY_ID must be an integer") from error

    return DeyeCredentials(
        values["DEYE_APP_ID"],
        values["DEYE_APP_SECRET"],
        values["DEYE_ACCOUNT_EMAIL"],
        values["DEYE_ACCOUNT_PASSWORD"],
        company_id,
    )

def discover_pilots(api: DeyeReadOnlyClient) -> tuple[dict[str, str | int], ...]:
    """Return only approved pilot keys and their native station IDs."""
    body: dict[str, Any] = api.list_stations(api.obtain_token())
    data: Any = body.get("data", body)
    rows = (
        data
        if isinstance(data, list)
        else data.get("records", data.get("list", data.get("stationList", [])))
        if isinstance(data, dict)
        else []
    )
    selected: list[dict[str, str | int]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = next(
            (
                row.get(key)
                for key in ("stationName", "name", "plantName")
                if isinstance(row.get(key), str)
            ),
            None,
        )
        station_id = next(
            (row.get(key) for key in ("stationId", "id") if isinstance(row.get(key), int)),
            None,
        )
        pilot_key = next(
            (
                key
                for prefix, key in PILOTS_BY_NAME_PREFIX.items()
                if name and name.strip().casefold().startswith(prefix.casefold())
            ),
            None,
        )
        if pilot_key and station_id and station_id > 0:
            selected.append({"pilot_key": pilot_key, "station_id": station_id})

    expected = set(PILOTS_BY_NAME_PREFIX.values())
    if {row["pilot_key"] for row in selected} != expected:
        raise ValueError("Deye response did not contain both approved pilot stations")
    return tuple(sorted(selected, key=lambda row: str(row["pilot_key"])))

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="allow bounded read-only API calls")
    if not parser.parse_args().execute:
        raise SystemExit("dry run: pass --execute after loading Deye secrets into the environment")
    client = DeyeReadOnlyClient(credentials_from_environment())
    try:
        selected = discover_pilots(client)
    except DeyeApiError as error:
        print(json.dumps({
            "outcome": "rejected", "endpoint": error.endpoint,
            "status_code": error.status_code, "provider_code": error.provider_code,
        }, ensure_ascii=False))
        raise SystemExit(2)
    print(json.dumps({"outcome": "completed", "selected_pilots": selected}, ensure_ascii=False))

if __name__ == "__main__": main()
