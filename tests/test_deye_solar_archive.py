from datetime import date, datetime
import pytest
from app.deye_solar_archive import archive_window


def test_window_accepts_single_day_and_31_days():
    assert archive_window(date(2020,1,1),date(2020,1,1))
    assert archive_window(date(2020,1,1),date(2020,1,31))


@pytest.mark.parametrize('start,end',[(date(2020,1,2),date(2020,1,1)),
    (date(2020,1,1),date(2020,2,1)),(datetime(2020,1,1),date(2020,1,2)),
    ('2020-01-01',date(2020,1,2))])
def test_ambiguous_or_unbounded_window_rejected(start,end):
    with pytest.raises(ValueError): archive_window(start,end)
