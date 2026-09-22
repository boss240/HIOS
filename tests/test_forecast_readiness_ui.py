from pathlib import Path


def test_forecast_readiness_is_a_separate_utf8_dashboard_module():
    root = Path(__file__).resolve().parents[1]
    page = (root / "web" / "index.html").read_text(encoding="utf-8")
    script = (root / "web" / "forecast-readiness.js").read_text(encoding="utf-8")
    assert 'id="forecastReadinessList"' in page
    assert '/assets/forecast-readiness.js' in page
    assert '/dashboard/forecast-readiness' in script
    assert 'innerHTML' not in script
    assert 'calibrated' in script

