"""Normalize explicit device PV power, preserving gaps before integration."""
import math
import re
from app.deye_power_integration import integrate_power_day


def solar_power_samples(body):
    """Require epoch-second timestamps and explicit W, never infer station units.

    Missing/non-numeric power breaks interpolation. Structural, timestamp,
    duplicate-key and unit ambiguity reject the response. Device IDs are omitted.
    """
    rows = body.get('dataList')
    if not isinstance(rows, list):
        raise ValueError('device dataList required')
    samples = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('history object required')
        stamp = row.get('time')
        if isinstance(stamp, str) and re.fullmatch(r'[0-9]{10}', stamp):
            stamp = int(stamp)
        if (isinstance(stamp, bool) or not isinstance(stamp, int)
                or not 1_000_000_000 <= stamp <= 9_999_999_999):
            raise ValueError('explicit epoch seconds required')
        if samples and stamp <= samples[-1]['timeStamp']:
            raise ValueError('timestamps must strictly increase')
        items = row.get('itemList')
        if not isinstance(items, list) or any(not isinstance(i, dict) for i in items):
            raise ValueError('history itemList required')
        solar = [i for i in items if i.get('key') == 'TotalSolarPower']
        if len(solar) > 1:
            raise ValueError('duplicate solar power measurement')
        power = None
        if solar:
            if solar[0].get('unit') != 'W':
                raise ValueError('explicit solar power unit W required')
            value = solar[0].get('value')
            if not isinstance(value, bool) and isinstance(value, (str, int, float)):
                try:
                    power = float(value)
                except (ValueError, OverflowError):
                    power = None
                if power is not None and (not math.isfinite(power) or power < 0):
                    power = None
        samples.append({'timeStamp': stamp, 'generationPower': power})
    return tuple(samples)


def solar_hourly_preview(body, *, day, max_gap_seconds=600):
    """Derived device PV energy only; does not assert full plant coverage."""
    return integrate_power_day(solar_power_samples(body), day=day, power_unit='W',
                               max_gap_seconds=max_gap_seconds)
