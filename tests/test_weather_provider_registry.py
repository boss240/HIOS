import pytest

from app.weather_provider_registry import configure_channel, list_channels

pytest_plugins = ["test_runtime"]


def test_weather_channels_are_tenant_scoped_and_updatable(db):
    configured = configure_channel(database_url=db, tenant_id="a", subject="alice", provider="eosda_weather", role="research")
    assert configured.status == "candidate"
    updated = configure_channel(database_url=db, tenant_id="a", subject="alice", provider="eosda_weather", role="challenger", status="configured")
    assert updated.role == "challenger"
    assert list_channels(database_url=db, tenant_id="a", subject="alice") == (updated,)
    with pytest.raises(PermissionError):
        list_channels(database_url=db, tenant_id="a", subject="bob")


def test_weather_channel_rejects_unknown_provider(db):
    with pytest.raises(ValueError, match="catalog"):
        configure_channel(database_url=db, tenant_id="a", subject="alice", provider="unknown", role="research")