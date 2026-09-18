"""Run one bounded, read-only Deye frame-history collection for both pilots."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.deye_hourly_collection import collect_closed_pilot_day
from app.deye_openapi import DeyeApiError, DeyeReadOnlyClient
from scripts.deye_pilot_discovery import credentials_from_environment, discover_pilots


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, type=date.fromisoformat,
                        help="one closed UTC day in YYYY-MM-DD format")
    parser.add_argument("--execute", action="store_true", help="allow the bounded Deye read calls")
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("dry run: pass --execute after loading Deye secrets into the environment")

    client = DeyeReadOnlyClient(credentials_from_environment())
    try:
        pilots = discover_pilots(client)
        results = []
        for pilot in pilots:
            report = collect_closed_pilot_day(
                client, station_id=int(pilot["station_id"]), closed_day_utc=args.date,
            )
            results.append({"pilotKey": pilot["pilot_key"], "report": report})
    except (DeyeApiError, ValueError) as error:
        detail = {
            "outcome": "rejected", "endpoint": getattr(error, "endpoint", None),
            "statusCode": getattr(error, "status_code", None),
            "providerCode": getattr(error, "provider_code", None),
        }
        print(json.dumps(detail, ensure_ascii=False))
        raise SystemExit(2)

    print(json.dumps({"outcome": "completed", "collection": results}, ensure_ascii=False))


if __name__ == "__main__":
    main()
