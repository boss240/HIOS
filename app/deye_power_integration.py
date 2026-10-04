"""Integrate instantaneous power without inventing coverage or provider units.

These are derived estimates, not meter readings. The caller must establish the
unit and field semantics before persisting results as forecasting evidence.
"""
from datetime import date, datetime, time, timezone
import math


def integrate_power_day(rows, *, day: date, power_unit: str, max_gap_seconds: int = 600):
    """Return 24 UTC hours using piecewise linear power and clipped boundaries.

    A missing/invalid power sample breaks interpolation. Long gaps are omitted;
    no extrapolation fills the beginning/end of a day. Duplicate or unordered
    timestamps reject the batch. Boundary samples outside the day are allowed.
    """
    if isinstance(day, datetime) or not isinstance(day, date):
        raise ValueError('day must be a date')
    if power_unit not in ('W', 'kW'):
        raise ValueError('explicit W or kW unit required')
    if isinstance(max_gap_seconds, bool) or not isinstance(max_gap_seconds, int) or not 1 <= max_gap_seconds <= 900:
        raise ValueError('gap limit must be 1..900 seconds')
    origin = int(datetime.combine(day, time(), timezone.utc).timestamp())
    samples = []
    for row in rows:
        stamp = row.get('timeStamp')
        if isinstance(stamp, bool) or not isinstance(stamp, (int, float)) or not math.isfinite(stamp) or int(stamp) != stamp or not 1_000_000_000 <= stamp <= 9_999_999_999:
            raise ValueError('invalid epoch seconds')
        if samples and stamp <= samples[-1][0]:
            raise ValueError('timestamps must strictly increase')
        power = row.get('generationPower')
        valid = not isinstance(power, bool) and isinstance(power, (int, float)) and math.isfinite(power) and power >= 0
        samples.append((int(stamp), float(power) / (1000 if power_unit == 'W' else 1) if valid else None))
    energy = [0.0] * 24
    coverage = [0] * 24
    for (start, p0), (end, p1) in zip(samples, samples[1:]):
        if p0 is None or p1 is None or end-start > max_gap_seconds:
            continue
        left, right = max(start, origin), min(end, origin+86400)
        while left < right:
            hour = (left-origin)//3600
            stop = min(right, origin+(hour+1)*3600)
            a = p0+(p1-p0)*(left-start)/(end-start)
            b = p0+(p1-p0)*(stop-start)/(end-start)
            energy[hour] += (a/2+b/2)*(stop-left)/3600
            coverage[hour] += stop-left
            left = stop
    if any(not math.isfinite(value) for value in energy):
        raise ValueError('nonfinite integrated energy')
    return tuple({'hourUtc':datetime.fromtimestamp(origin+h*3600, timezone.utc).isoformat(),
                  'derivedEnergyKwh':energy[h] if coverage[h] else None,
                  'coveredSeconds':coverage[h], 'complete':coverage[h] == 3600,
                  'method':'linear_power_integration'} for h in range(24))
