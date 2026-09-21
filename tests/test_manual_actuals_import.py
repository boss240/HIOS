import base64
from io import BytesIO

from openpyxl import Workbook

from app.manual_actuals_import import preview_manual_actuals_csv, preview_manual_actuals_xlsx


def test_preview_accepts_template_rows_without_persisting():
    result = preview_manual_actuals_csv('plant_key,interval_start_utc,interval_end_utc,ac_power_kw,energy_kwh,energy_semantics,device_status,source_reference\n'
        'deye-pilot-pohreby,2026-09-18T08:00:00Z,2026-09-18T09:00:00Z,10,9,interval,online,export-a\n')
    assert result == {'rows': 1, 'byPilot': {'deye-pilot-pohreby': 1, 'deye-pilot-borshchiv': 0}, 'persistence': 'not_written_pending_field_mapping'}


def test_preview_rejects_missing_headers_and_unknown_pilot():
    try: preview_manual_actuals_csv('a,b\n1,2\n')
    except ValueError as error: assert 'headers' in str(error)
    else: raise AssertionError('expected validation failure')


def test_preview_accepts_hios_template_xlsx():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Hourly actuals'
    sheet.append(['plant_key', 'interval_start_utc', 'interval_end_utc', 'ac_power_kw', 'energy_kwh', 'energy_semantics', 'device_status', 'source_reference'])
    sheet.append(['deye-pilot-borshchiv', '2026-09-18T08:00:00Z', '2026-09-18T09:00:00Z', 10, 9, 'interval', 'online', 'export-b'])
    stream = BytesIO()
    workbook.save(stream)
    result = preview_manual_actuals_xlsx(base64.b64encode(stream.getvalue()).decode('ascii'))
    assert result['rows'] == 1
    assert result['byPilot']['deye-pilot-borshchiv'] == 1
