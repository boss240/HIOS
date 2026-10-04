import base64
from io import BytesIO

from openpyxl import Workbook

from app.manual_actuals_import import preview_manual_actuals_csv, preview_manual_actuals_xlsx


def test_preview_accepts_template_rows_without_persisting():
    result = preview_manual_actuals_csv('plant_key,interval_start_utc,interval_end_utc,ac_power_kw,energy_kwh,energy_semantics,device_status,source_reference\n'
        'deye-pilot-pohreby,2026-09-18T08:00:00Z,2026-09-18T09:00:00Z,10,9,interval,online,export-a\n')
    assert result['rows'] == 1
    assert result['byPilot'] == {'deye-pilot-pohreby': 1, 'deye-pilot-borshchiv': 0}
    assert result['quality']['deye-pilot-pohreby'] == {
        'rows': 1, 'uniqueIntervals': 1, 'duplicateIntervals': 0, 'gapCount': 0,
        'missingHours': 0, 'overlapCount': 0,
        'firstIntervalStartUtc': '2026-09-18T08:00:00Z', 'lastIntervalEndUtc': '2026-09-18T09:00:00Z',
    }
    assert result['persistence'] == 'not_written_pending_field_mapping'


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


def test_preview_reports_gaps_and_duplicate_hourly_intervals():
    result = preview_manual_actuals_csv(
        'plant_key,interval_start_utc,interval_end_utc,ac_power_kw,energy_kwh,energy_semantics,device_status,source_reference\n'
        'deye-pilot-borshchiv,2026-09-18T08:00:00Z,2026-09-18T09:00:00Z,10,9,interval,online,export-b\n'
        'deye-pilot-borshchiv,2026-09-18T08:00:00Z,2026-09-18T09:00:00Z,10,9,interval,online,export-b\n'
        'deye-pilot-borshchiv,2026-09-18T11:00:00Z,2026-09-18T12:00:00Z,10,9,interval,online,export-b\n'
    )
    quality = result['quality']['deye-pilot-borshchiv']
    assert quality['duplicateIntervals'] == 1
    assert quality['gapCount'] == 1
    assert quality['missingHours'] == 2


def test_preview_rejects_non_hourly_rows():
    try:
        preview_manual_actuals_csv(
            'plant_key,interval_start_utc,interval_end_utc,ac_power_kw,energy_kwh,energy_semantics,device_status,source_reference\n'
            'deye-pilot-pohreby,2026-09-18T08:00:00Z,2026-09-18T08:30:00Z,10,9,interval,online,export-a\n'
        )
    except ValueError as error:
        assert 'exactly one hour' in str(error)
    else:
        raise AssertionError('expected hourly validation failure')
