"""Normalize an owner-supplied Deye station ID or Deye Cloud station link."""
from __future__ import annotations

from urllib.parse import parse_qs, urlsplit


def station_id_from_reference(value: object) -> str:
    """Return a canonical positive Deye station ID without fetching any URL.

    Owners commonly copy the full ``deyecloud.com/station/basic?id=...`` link
    from a browser. Accepting that link avoids a manual copy-and-edit step.
    Only a numeric ID or HTTPS Deye Cloud station URL is accepted.
    """
    if not isinstance(value, str):
        raise ValueError("Deye station reference is required")
    candidate = value.strip()
    if candidate.isdecimal() and 1 <= len(candidate) <= 18 and int(candidate) > 0:
        return str(int(candidate))

    parsed = urlsplit(candidate)
    host = (parsed.hostname or "").casefold()
    if parsed.scheme != "https" or not (host == "deyecloud.com" or host.endswith(".deyecloud.com")):
        raise ValueError("A Deye station ID or Deye Cloud link is required")
    if not parsed.path.rstrip("/").casefold().endswith("/station/basic"):
        raise ValueError("The Deye link must identify a station")
    values = parse_qs(parsed.query, keep_blank_values=True).get("id", [])
    if len(values) != 1:
        raise ValueError("The Deye link must contain one station ID")
    return station_id_from_reference(values[0])
