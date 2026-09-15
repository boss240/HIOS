"""Run exactly one read-only Google Weather plus Solcast forecast request."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from app.controlled_weather_retrieval import retrieve_operational_weather
from app.pilot_sites import PILOT_SITES, pilot_site
from app.weather_provider_clients import GoogleWeatherReadClient, SolcastReadClient
from app.weather_provider_credentials import operational_credentials_from_environment
from app.weather_provider_requests import GoogleHourlyForecastRequest, SolcastRadiationForecastRequest


def run(site_key: str, hours: int) -> dict[str, object]:
    """Perform one explicit read. This function neither persists nor schedules work."""
    site = pilot_site(site_key)
    credentials = operational_credentials_from_environment()
    result = retrieve_operational_weather(
        google=GoogleWeatherReadClient(credentials.google_weather),
        solcast=SolcastReadClient(credentials.solcast),
        google_request=GoogleHourlyForecastRequest(site.latitude, site.longitude, hours),
        solcast_request=SolcastRadiationForecastRequest(site.latitude, site.longitude),
    )
    intervals = result.intervals[:hours]
    return {
        "site": {"key": site.key, "name": site.display_name,
                 "latitude": site.latitude, "longitude": site.longitude},
        "retrievedAtUtc": datetime.now(timezone.utc).isoformat(),
        "googleIntervalCount": result.google_interval_count,
        "solcastIntervalCount": result.solcast_interval_count,
        "composedIntervalCount": len(intervals),
        "firstIntervalUtc": intervals[0].valid_at_utc.isoformat() if intervals else None,
        "lastIntervalUtc": intervals[-1].interval_end_utc.isoformat() if intervals else None,
        "status": "read_only_preview",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", choices=sorted(PILOT_SITES), required=True)
    parser.add_argument("--hours", type=int, default=24, choices=range(1, 25))
    args = parser.parse_args()
    print(json.dumps(run(args.site, args.hours), ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
