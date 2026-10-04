"""Non-sensitive device measurement unit inventory, never a station mapping."""
from collections import defaultdict


def measurement_units(body: dict) -> tuple[dict, ...]:
    """Summarise only measurement keys and units, excluding serials and values.

    Multiple units on the same key are a conflict. This does not establish that
    a device key equals station generationPower or approve either semantics.
    """
    rows = body.get('deviceDataList')
    if not isinstance(rows, list):
        raise ValueError('deviceDataList required')
    units = defaultdict(set)
    for device in rows:
        if not isinstance(device, dict) or not isinstance(device.get('dataList'), list):
            raise ValueError('device dataList required')
        for item in device['dataList']:
            if not isinstance(item,dict):raise ValueError('measurement object required')
            key, unit = item.get('key'), item.get('unit')
            if not isinstance(key,str) or not key.strip() or len(key)>128:
                raise ValueError('measurement key required')
            if not isinstance(unit,str) or not unit.strip() or len(unit)>32:
                raise ValueError('measurement unit required')
            units[key].add(unit)
    return tuple({'key':key,'units':sorted(values),'conflict':len(values)>1}
                 for key,values in sorted(units.items()))
