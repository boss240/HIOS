from app.deye_station_discovery import DeyeStationCandidate, station_candidates

def test_discovers_only_complete_station_candidates():
    rows={'data':{'records':[{'stationId':7,'stationName':'Pohreby'},{'id':9,'name':'Borshchiv'},{'stationId':'bad','stationName':'Ignore'}]}}
    assert station_candidates(rows) == (DeyeStationCandidate(9,'Borshchiv'),DeyeStationCandidate(7,'Pohreby'))

def test_empty_or_unknown_shape_has_no_candidates():
    assert station_candidates({'data':{'records':'invalid'}})==()