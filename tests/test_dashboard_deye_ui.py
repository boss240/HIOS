from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_offers_an_explicit_read_only_telemetry_audit_after_station_selection():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "web" / "deye-discovery.js").read_text(encoding="utf-8")

    assert 'id="deyeTelemetryAudit"' in html
    assert 'id="deyeAuditDate"' in html
    assert 'id="auditDeyeTelemetry"' in html
    assert "confirmReadOnly: true" in script
    assert "/telemetry-audit`" in script
    assert "persistence" not in script
