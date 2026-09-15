import pytest

from app.inverter_cloud import InverterCloudProvider
from app.inverter_connection_request import list_connection_requests, request_connection

pytest_plugins = ["test_runtime"]


def test_cloud_connection_request_is_idempotent_and_tenant_safe(db):
    first = request_connection(database_url=db, tenant_id="a", subject="alice", plant_id="002", provider=InverterCloudProvider.DEYE_CLOUD)
    second = request_connection(database_url=db, tenant_id="a", subject="alice", plant_id="002", provider=InverterCloudProvider.DEYE_CLOUD)
    assert second.request_id == first.request_id
    assert list_connection_requests(database_url=db, tenant_id="a", subject="alice", plant_id="002") == (first,)
    with pytest.raises(PermissionError):
        request_connection(database_url=db, tenant_id="a", subject="bob", plant_id="002", provider=InverterCloudProvider.DEYE_CLOUD)