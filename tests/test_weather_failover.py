import pytest

from app.weather_failover import (
    ProviderConfigurationError, ProviderError, RetryPolicy, WeatherRetrievalBlocked,
    retrieve_with_failover,
)


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def sequence(*items):
    values = iter(items)

    def call():
        item = next(values)
        if isinstance(item, Exception):
            raise item
        return item

    return call


def retrieve(primary, secondary, *, policy=RetryPolicy()):
    clock = FakeClock()
    result = retrieve_with_failover(
        primary_name="primary", primary=primary, secondary_name="secondary", secondary=secondary,
        policy=policy, clock=clock, sleep=clock.sleep,
    )
    return result, clock


def test_retries_transient_primary_failure_then_returns_fresh_value():
    result, clock = retrieve(sequence(ProviderError("timeout"), {"ghi": 500}), sequence({"ghi": 400}))

    assert result.provider == "primary"
    assert result.degraded is False
    assert result.value == {"ghi": 500}
    assert result.events[0].retry_delay_seconds == 1.0
    assert clock.sleeps == [1.0]


def test_uses_secondary_after_primary_attempt_budget_is_exhausted():
    result, _ = retrieve(
        sequence(ProviderError("5xx", status_code=503), ProviderError("5xx", status_code=503), ProviderError("5xx", status_code=503)),
        sequence({"ghi": 450}),
    )

    assert result.provider == "secondary"
    assert result.degraded is True
    assert [event.attempt for event in result.events] == [1, 2, 3]


def test_retry_after_outside_deadline_falls_back_without_sleeping():
    result, clock = retrieve(
        sequence(ProviderError("rate limited", status_code=429, retry_after_seconds=60)),
        sequence({"ghi": 450}),
        policy=RetryPolicy(total_budget_seconds=30),
    )

    assert result.provider == "secondary"
    assert clock.sleeps == []


def test_configuration_fault_fails_closed_without_calling_secondary():
    called = False

    def secondary():
        nonlocal called
        called = True
        return {"ghi": 450}

    with pytest.raises(ProviderConfigurationError):
        retrieve(sequence(ProviderError("unauthorized", status_code=401)), secondary)

    assert called is False


def test_all_transient_failures_are_reported_without_stale_value():
    clock = FakeClock()
    with pytest.raises(WeatherRetrievalBlocked) as exc_info:
        retrieve_with_failover(
            primary_name="primary", primary=sequence(ProviderError("down", status_code=503)),
            secondary_name="secondary", secondary=sequence(ProviderError("down", status_code=503)),
            policy=RetryPolicy(attempts_per_provider=1), clock=clock, sleep=clock.sleep,
        )

    assert [event.provider for event in exc_info.value.events] == ["primary", "secondary"]
