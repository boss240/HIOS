import pytest

from app.deye_station_reference import station_id_from_reference


def test_accepts_numeric_deye_station_id():
    assert station_id_from_reference(" 061205012 ") == "61205012"


def test_accepts_station_link_copied_from_deye_cloud():
    link = "https://www.deyecloud.com/station/basic?id=61205012"
    assert station_id_from_reference(link) == "61205012"


@pytest.mark.parametrize("value", ["0", "-3", "station=5", "https://example.test/station/basic?id=5",
                                  "https://www.deyecloud.com/setting/home?id=5", "https://www.deyecloud.com/station/basic?id=5&id=6"])
def test_rejects_ambiguous_or_non_deye_references(value):
    with pytest.raises(ValueError):
        station_id_from_reference(value)
