from datetime import datetime, timedelta, timezone
from io import BytesIO

from openpyxl import load_workbook
import pytest

from app.hourly_planning import HourlyForecast, csv_export, hourly_plan, xlsx_export


def forecast(hour=0, energy=5.0):
    start = datetime(2026, 9, 16, hour, tzinfo=timezone.utc)
    return HourlyForecast(start, start + timedelta(hours=1), energy, energy, ("source_verified",))


def test_hourly_plan_mixes_consumption_and_rdn_without_trading():
    plan = hourly_plan((forecast(0, 5), forecast(1, 12)), [8, 4], [6.5, 4.0])
    assert plan[0].net_grid_kwh == 3
    assert plan[0].estimated_import_cost_uah == 19.5
    assert plan[1].net_grid_kwh == -8
    assert plan[1].estimated_export_value_uah == 32
    assert plan[0].quality_flags == ("source_verified",)


def test_hourly_plan_rejects_unaligned_or_invalid_scenarios():
    with pytest.raises(ValueError, match="one value"):
        hourly_plan((forecast(),), [1, 2])
    with pytest.raises(ValueError, match="finite non-negative"):
        hourly_plan((forecast(),), [-1])


def test_hourly_exports_are_excel_readable_and_include_hourly_values():
    plan = hourly_plan((forecast(),), [8], [6.5])
    csv = csv_export(plan)
    assert "estimated_import_cost_uah" in csv
    book = load_workbook(BytesIO(xlsx_export(plan)), data_only=True)
    sheet = book["Hourly plan"]
    assert sheet["D2"].value == 5
    assert sheet["E2"].value == 8
    assert sheet["H2"].value == 19.5
