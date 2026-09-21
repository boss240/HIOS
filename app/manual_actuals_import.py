"""Validate a manual Deye hourly CSV before any field mapping or persistence."""
from __future__ import annotations

import base64
import csv
from datetime import datetime, timezone
from io import BytesIO, StringIO
import math
import hashlib
from uuid import uuid4
from zipfile import BadZipFile

import psycopg
from psycopg.types.json import Jsonb
from openpyxl import load_workbook

_REQUIRED = ("plant_key", "interval_start_utc", "interval_end_utc", "ac_power_kw", "energy_kwh", "energy_semantics", "device_status", "source_reference")
_PILOTS = {"deye-pilot-pohreby", "deye-pilot-borshchiv"}


def _utc(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as error:
        raise ValueError(f"{label} must be ISO 8601 UTC") from error
    if parsed.tzinfo is None or parsed.astimezone(timezone.utc) != parsed:
        raise ValueError(f"{label} must be UTC")
    return parsed


def _number(value: str, label: str) -> None:
    if not value.strip():
        return
    try:
        number = float(value)
    except ValueError as error:
        raise ValueError(f"{label} must be numeric") from error
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{label} must be finite and non-negative")


def _validated_rows(content: str) -> list[dict[str, object]]:
    if not isinstance(content, str) or len(content.encode("utf-8")) > 2_000_000:
        raise ValueError("CSV must be non-empty and at most 2 MB")
    rows = [line for line in content.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    reader = csv.DictReader(StringIO("\n".join(rows)))
    if tuple(reader.fieldnames or ()) != _REQUIRED:
        raise ValueError("CSV headers do not match the HIOS Deye template")
    parsed_rows: list[dict[str, object]] = []
    for position, row in enumerate(reader, start=2):
        pilot = (row.get("plant_key") or "").strip()
        if pilot not in _PILOTS:
            raise ValueError(f"row {position}: unknown pilot key")
        start = _utc(row["interval_start_utc"], f"row {position} interval_start_utc")
        end = _utc(row["interval_end_utc"], f"row {position} interval_end_utc")
        if end <= start:
            raise ValueError(f"row {position}: interval end must be after start")
        _number(row["ac_power_kw"], f"row {position} ac_power_kw")
        _number(row["energy_kwh"], f"row {position} energy_kwh")
        if not row["ac_power_kw"].strip() and not row["energy_kwh"].strip():
            raise ValueError(f"row {position}: power or energy is required")
        if row["energy_kwh"].strip() and row["energy_semantics"] not in {"interval", "cumulative"}:
            raise ValueError(f"row {position}: energy_semantics is invalid")
        if not (row["source_reference"] or "").strip():
            raise ValueError(f"row {position}: source_reference is required")
        parsed_rows.append({"pilot": pilot, "start": start, "end": end,
                            "power": float(row["ac_power_kw"]) if row["ac_power_kw"].strip() else None,
                            "energy": float(row["energy_kwh"]) if row["energy_kwh"].strip() else None,
                            "semantics": row["energy_semantics"] or None,
                            "status": (row["device_status"] or "").strip() or None,
                            "reference": row["source_reference"].strip()})
    return parsed_rows


def preview_manual_actuals_csv(content: str) -> dict[str, object]:
    parsed_rows = _validated_rows(content)
    counts = {pilot: 0 for pilot in _PILOTS}
    for row in parsed_rows:
        counts[row["pilot"]] += 1
    if not sum(counts.values()):
        raise ValueError("CSV has no data rows")
    return {"rows": sum(counts.values()), "byPilot": counts, "persistence": "not_written_pending_field_mapping"}


def _xlsx_as_csv(content_base64: str) -> str:
    """Read a HIOS-template workbook without accepting arbitrary source mappings."""
    if not isinstance(content_base64, str) or not content_base64:
        raise ValueError("XLSX must be provided as base64")
    try:
        content = base64.b64decode(content_base64, validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError("XLSX encoding is invalid") from error
    if len(content) > 2_000_000:
        raise ValueError("XLSX must be at most 2 MB")
    try:
        workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        sheet = workbook["Hourly actuals"] if "Hourly actuals" in workbook.sheetnames else workbook.active
        output = StringIO(newline="")
        writer = csv.writer(output)
        for row in sheet.iter_rows(values_only=True):
            writer.writerow([
                value.isoformat().replace("+00:00", "Z") if isinstance(value, datetime) else "" if value is None else value
                for value in row
            ])
        workbook.close()
        return output.getvalue()
    except (BadZipFile, OSError, ValueError, KeyError) as error:
        raise ValueError("XLSX cannot be read") from error


def preview_manual_actuals_xlsx(content_base64: str) -> dict[str, object]:
    return preview_manual_actuals_csv(_xlsx_as_csv(content_base64))


def persist_manual_actuals_csv(*, database_url: str, tenant_id: str, subject: str, content: str) -> dict[str, object]:
    rows = _validated_rows(content)
    labels = {"deye-pilot-pohreby": "Погреби", "deye-pilot-borshchiv": "Борщів"}
    inserted = skipped = 0
    with psycopg.connect(database_url, connect_timeout=5) as connection:
        if connection.execute("SELECT 1 FROM membership WHERE tenant_id=%s AND subject=%s AND active", (tenant_id, subject)).fetchone() is None:
            raise PermissionError("active membership is required")
        for plant_id, name in labels.items():
            connection.execute("INSERT INTO plant(public_id,tenant_id,name) VALUES (%s,%s,%s) ON CONFLICT (public_id) DO NOTHING", (plant_id, tenant_id, name))
        retrieved = datetime.now(timezone.utc)
        for row in rows:
            digest = hashlib.sha256("|".join(str(row[k]) for k in ("pilot", "start", "end", "power", "energy", "semantics", "status", "reference")).encode()).hexdigest()
            result = connection.execute("""INSERT INTO actual_generation_snapshot(snapshot_id,tenant_id,plant_id,provider,mapping_version,observed_at_utc,interval_end_utc,retrieved_at_utc,source_reference,payload_sha256,ac_power_kw,energy_kwh,energy_semantics,device_status,quality_flags) VALUES (%s,%s,%s,'deye_cloud','deye-manual-csv-v1',%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT (tenant_id,plant_id,provider,mapping_version,observed_at_utc,interval_end_utc,payload_sha256) DO NOTHING RETURNING snapshot_id""", (uuid4(),tenant_id,row["pilot"],row["start"],row["end"],retrieved,row["reference"],digest,row["power"],row["energy"],row["semantics"],row["status"],Jsonb(["manual_export"]))).fetchone()
            inserted += bool(result); skipped += not bool(result)
    return {"rows": len(rows), "inserted": inserted, "duplicates": skipped, "persistence": "written"}


def persist_manual_actuals_xlsx(*, database_url: str, tenant_id: str, subject: str, content_base64: str) -> dict[str, object]:
    return persist_manual_actuals_csv(
        database_url=database_url,
        tenant_id=tenant_id,
        subject=subject,
        content=_xlsx_as_csv(content_base64),
    )
