"""Approved coordinates for caller-invoked, non-production pilot weather reads."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PilotSite:
    key: str
    display_name: str
    latitude: float
    longitude: float


PILOT_SITES = {
    "pohreby": PilotSite("pohreby", "Погреби", 50.54085, 30.62605),
    "borshchiv": PilotSite("borshchiv", "Борщів", 50.30139, 31.31209),
}


def pilot_site(key: str) -> PilotSite:
    try:
        return PILOT_SITES[key]
    except KeyError as error:
        raise ValueError(f"unknown pilot site: {key}") from error
