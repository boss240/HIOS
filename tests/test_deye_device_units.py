import pytest
from app.deye_device_units import measurement_units

def test_inventory_omits_serial_values_and_detects_conflicting_units():
    body={'deviceDataList':[{'deviceSn':'private','dataList':[
        {'key':'PV Power','unit':'W','value':1200},
        {'key':'PV Power','unit':'kW','value':1.2},
        {'key':'Production','unit':'kWh','value':5}]}]}
    result=measurement_units(body)
    assert result == ({'key':'PV Power','units':['W','kW'],'conflict':True},
                      {'key':'Production','units':['kWh'],'conflict':False})
    assert 'private' not in str(result) and '1200' not in str(result)

@pytest.mark.parametrize('body',[{}, {'deviceDataList':[{}]}, {'deviceDataList':[{'dataList':[{}]}]},
    {'deviceDataList':[{'dataList':[{'key':'power','unit':None}]}]}])
def test_incomplete_metadata_fails_explicitly(body):
    with pytest.raises(ValueError):measurement_units(body)
