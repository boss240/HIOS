"""Read-only extraction of selectable Deye stations from an approved station-list response."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping

@dataclass(frozen=True)
class DeyeStationCandidate:
    station_id: int
    name: str

def station_candidates(body: Mapping[str, Any]) -> tuple[DeyeStationCandidate, ...]:
    data=body.get('data', body)
    rows=data if isinstance(data,list) else data.get('records',data.get('list',data.get('stationList',[]))) if isinstance(data,Mapping) else []
    found=[]
    for row in rows:
        if not isinstance(row,Mapping): continue
        name=next((row.get(k) for k in ('stationName','name','plantName') if isinstance(row.get(k),str) and row.get(k).strip()),None)
        station_id=next((row.get(k) for k in ('stationId','id') if isinstance(row.get(k),int) and not isinstance(row.get(k),bool) and row.get(k)>0),None)
        if name is not None and station_id is not None: found.append(DeyeStationCandidate(station_id,name.strip()))
    return tuple(sorted({item.station_id:item for item in found}.values(),key=lambda item:(item.name.casefold(),item.station_id)))