import pytest
from app.weather_capture_job import plant_scope

@pytest.mark.parametrize('scope',['[]','["a","a"]','["a","b","c"]','{}','[true]','[""]','not-json'])
def test_job_rejects_unbounded_or_ambiguous_plant_scope(scope):
    with pytest.raises(ValueError):plant_scope(scope)

def test_job_preserves_explicit_scope():
    assert plant_scope('["a","b"]') == ('a','b')
