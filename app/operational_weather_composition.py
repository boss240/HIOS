"""Exact-interval composition of the approved Google and Solcast roles."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math

from app.weather_provider_response import ProviderWeatherInterval


class OperationalWeatherCompositionError(ValueError):
    """Provider intervals cannot form a safe operational weather input."""


@dataclass(frozen=True)
class OperationalWeatherInterval:
    valid_at_utc: datetime
    interval_end_utc: datetime
    irradiance_global_wm2: float
    irradiance_direct_wm2: float
    irradiance_diffuse_wm2: float
    cloud_cover_pct: float
    temperature_c: float
    wind_speed_ms: float
    field_providers: tuple[tuple[str, str], ...]


_GOOGLE_FIELDS = frozenset({"cloud_cover_pct", "temperature_c", "wind_speed_ms"})
_SOLCAST_FIELDS = frozenset({
    "irradiance_global_wm2", "irradiance_direct_wm2", "irradiance_diffuse_wm2",
})


def _index(records: tuple[ProviderWeatherInterval, ...], provider: str) -> dict[tuple[datetime, datetime], ProviderWeatherInterval]:
    indexed: dict[tuple[datetime, datetime], ProviderWeatherInterval] = {}
    for record in records:
        if record.provider != provider:
            raise OperationalWeatherCompositionError(f"expected {provider} intervals only")
        key = (record.valid_at_utc, record.interval_end_utc)
        if key in indexed:
            raise OperationalWeatherCompositionError(f"duplicate {provider} interval")
        indexed[key] = record
    return indexed


def compose_operational_weather(*, google: tuple[ProviderWeatherInterval, ...],
                                solcast: tuple[ProviderWeatherInterval, ...]) -> tuple[OperationalWeatherInterval, ...]:
    """Compose only exact UTC matches; missing provider coverage fails closed."""
    google_by_interval = _index(google, "google_weather")
    solcast_by_interval = _index(solcast, "solcast")
    if not google_by_interval or not solcast_by_interval:
        raise OperationalWeatherCompositionError("both Google and Solcast interval sets are required")
    if google_by_interval.keys() != solcast_by_interval.keys():
        raise OperationalWeatherCompositionError("Google and Solcast intervals must match exactly")
    intervals = []
    for key in sorted(google_by_interval):
        google_record = google_by_interval[key]
        solcast_record = solcast_by_interval[key]
        if missing := _GOOGLE_FIELDS.difference(google_record.values):
            raise OperationalWeatherCompositionError("Google interval is missing required covariates: " + ", ".join(sorted(missing)))
        if missing := _SOLCAST_FIELDS.difference(solcast_record.values):
            raise OperationalWeatherCompositionError("Solcast interval is missing required irradiance: " + ", ".join(sorted(missing)))
        intervals.append(OperationalWeatherInterval(
            valid_at_utc=key[0], interval_end_utc=key[1],
            irradiance_global_wm2=solcast_record.values["irradiance_global_wm2"],
            irradiance_direct_wm2=solcast_record.values["irradiance_direct_wm2"],
            irradiance_diffuse_wm2=solcast_record.values["irradiance_diffuse_wm2"],
            cloud_cover_pct=google_record.values["cloud_cover_pct"],
            temperature_c=google_record.values["temperature_c"],
            wind_speed_ms=google_record.values["wind_speed_ms"],
            field_providers=(
                ("cloud_cover_pct", "google_weather"), ("temperature_c", "google_weather"),
                ("wind_speed_ms", "google_weather"),
                ("irradiance_global_wm2", "solcast"), ("irradiance_direct_wm2", "solcast"),
                ("irradiance_diffuse_wm2", "solcast"),
            ),
        ))
    return tuple(intervals)


def compose_hourly_operational_weather(*, google: tuple[ProviderWeatherInterval, ...],
                                       solcast: tuple[ProviderWeatherInterval, ...]) -> tuple[OperationalWeatherInterval, ...]:
    """Compose complete Google UTC hours with Solcast interval-mean irradiance.

    Solcast can extend beyond the Google horizon. Only exactly tiled hours are
    composed; missing coverage rejects the request instead of filling a gap.
    Original captures and their receipt/issue times must remain in provenance.
    This changes interval resolution, never forecast origin or capture times.
    """
    def checked(records, provider, fields):
        result = []
        for row in records:
            if row.provider != provider:
                raise OperationalWeatherCompositionError('unexpected provider')
            start, end = row.valid_at_utc, row.interval_end_utc
            if any(not isinstance(t,datetime) or t.tzinfo is None or t.utcoffset() is None for t in (start,end)):
                raise OperationalWeatherCompositionError('aware timestamps required')
            start, end = start.astimezone(timezone.utc), end.astimezone(timezone.utc)
            if end <= start or result and start < result[-1].interval_end_utc:
                raise OperationalWeatherCompositionError('ordered non-overlapping intervals required')
            if fields.difference(row.values):
                raise OperationalWeatherCompositionError('required interval-mean fields missing')
            values = {field:row.values[field] for field in fields}
            for field,value in values.items():
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
                    raise OperationalWeatherCompositionError('finite numeric fields required')
                if field != 'temperature_c' and value < 0 or field == 'cloud_cover_pct' and value > 100:
                    raise OperationalWeatherCompositionError('field outside physical range')
            result.append(ProviderWeatherInterval(provider,start,end,values))
        return tuple(result)
    hours = checked(google,'google_weather',_GOOGLE_FIELDS)
    radiation = checked(solcast,'solcast',_SOLCAST_FIELDS)
    aligned = []
    for hour in hours:
        start,end = hour.valid_at_utc,hour.interval_end_utc
        if start.minute or start.second or start.microsecond or end-start != timedelta(hours=1):
            raise OperationalWeatherCompositionError('Google intervals must be whole UTC hours')
        parts = [row for row in radiation if row.valid_at_utc < end and row.interval_end_utc > start]
        cursor = start
        means = dict.fromkeys(_SOLCAST_FIELDS,0.0)
        for part in parts:
            if part.valid_at_utc != cursor or part.interval_end_utc > end:
                raise OperationalWeatherCompositionError('Solcast must tile complete hours without clipping')
            seconds = (part.interval_end_utc-part.valid_at_utc).total_seconds()
            for field in means:means[field] += part.values[field]*(seconds/3600)
            cursor = part.interval_end_utc
        if cursor != end:
            raise OperationalWeatherCompositionError('Solcast hour coverage incomplete')
        aligned.append(ProviderWeatherInterval('solcast',start,end,means))
    return compose_operational_weather(google=hours,solcast=tuple(aligned))
