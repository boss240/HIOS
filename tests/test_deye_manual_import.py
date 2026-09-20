from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_shows_deye_status_and_offers_safe_manual_actuals_templates():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert 'id="integrationStatus"' in html
    assert 'Очікується відповідь Deye' in html
    assert '/downloads/hios-deye-hourly-actuals-template.csv' in html
    assert '/downloads/HIOS_Deye_Hourly_Actuals_Template.xlsx' in html


def test_manual_import_contract_names_pilot_keys_and_mapping_gate():
    document = (ROOT / "docs" / "integrations" / "deye-manual-hourly-import.md").read_text(encoding="utf-8")
    assert 'deye-pilot-pohreby' in document
    assert 'deye-pilot-borshchiv' in document
    assert 'Очікує перевірки' in document
