from pathlib import Path


def test_quick_onboarding_exposes_the_full_first_inverter_wave():
    page = (Path(__file__).resolve().parents[1] / "web/index.html").read_text(encoding="utf-8")
    for provider in (
        "deye_cloud", "huawei_fusionsolar", "goodwe_sems", "sungrow_isolarcloud",
        "solis_cloud", "growatt_shineserver", "solaredge_one", "sma_sunny_portal",
        "fronius_solar_web", "victron_vrm",
    ):
        assert f'value="{provider}"' in page
    assert "Дані доступу тут не вводяться" in page
