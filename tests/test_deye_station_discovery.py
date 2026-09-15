from app.deye_station_discovery import station_candidates

def test_discovers_only_complete_station_candidates():
    rows={'data':{'records':[{'stationId':7,'stationName':'Погреби'},{'id':9,'name':'Борщів'},{'stationId':'bad','stationName':'Ignore'},{'stationId':7,'stationName':'Duplicate'}]}}
    assert station_candidates(rows) == (type(station_candidates(rows)[0])(9,'Борщів'),type(station_candidates(rows)[0])(7,'Погреби'))

def test_empty_or_unknown_shape_has_no_candidates():
    assert station_candidates({'data':{'records':'invalid'}})==()