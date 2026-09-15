import pytest

from app.pilot_sites import PILOT_SITES, pilot_site


def test_two_selected_pilot_sites_have_exact_coordinates():
    assert set(PILOT_SITES) == {"pohreby", "borshchiv"}
    assert pilot_site("pohreby").latitude == 50.54085
    assert pilot_site("pohreby").longitude == 30.62605
    assert pilot_site("borshchiv").latitude == 50.30139
    assert pilot_site("borshchiv").longitude == 31.31209


def test_unknown_pilot_site_fails_closed():
    with pytest.raises(ValueError, match="unknown pilot site"):
        pilot_site("other")
