"""Provider-independent, bounded weather retrieval for Sprint 2 adapters.

The module deliberately has no HTTP client or provider credential handling.  An
adapter supplies a callable, so the policy can be tested and audited before a
provider is approved and configured.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar


T = TypeVar("T")


class ProviderError(Exception):
    """An adapter failure with an optional HTTP status and Retry-After value."""

    def __init__(self, message: str, *, status_code: int | None = None,
                 retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds


class ProviderConfigurationError(ProviderError):
    """Credentials, configuration, or schema need operator repair."""


class WeatherRetrievalBlocked(ProviderError):
    """No provider produced fresh data within the configured job budget."""

    def __init__(self, message: str, events: tuple["RetrievalEvent", ...]) -> None:
        super().__init__(message)
        self.events = events


@dataclass(frozen=True)
class RetryPolicy:
    total_budget_seconds: float = 30.0
    attempts_per_provider: int = 3
    base_backoff_seconds: float = 1.0

    def __post_init__(self) -> None:
        if self.total_budget_seconds <= 0:
            raise ValueError("total_budget_seconds must be positive")
        if self.attempts_per_provider < 1:
            raise ValueError("attempts_per_provider must be at least one")
        if self.base_backoff_seconds < 0:
            raise ValueError("base_backoff_seconds must not be negative")


@dataclass(frozen=True)
class RetrievalEvent:
    provider: str
    attempt: int
    status_code: int | None
    reason: str
    retry_delay_seconds: float | None = None


@dataclass(frozen=True)
class WeatherRetrieval(Generic[T]):
    provider: str
    value: T
    degraded: bool
    events: tuple[RetrievalEvent, ...]


def _transient(error: ProviderError) -> bool:
    return error.status_code == 429 or error.status_code is None or error.status_code >= 500


def retrieve_with_failover(*, primary_name: str, primary: Callable[[], T],
                            secondary_name: str, secondary: Callable[[], T],
                            policy: RetryPolicy = RetryPolicy(),
                            clock: Callable[[], float], sleep: Callable[[float], None]) -> WeatherRetrieval[T]:
    """Return fresh weather from primary or an approved secondary adapter.

    Authentication and schema faults fail closed.  Transient failures are retried
    only inside the deadline; after the primary is exhausted, the secondary gets
    the same bounded attempt policy.  It never returns stale data.
    """
    if not primary_name.strip() or not secondary_name.strip():
        raise ValueError("provider names must be non-empty")
    started_at = clock()
    events: list[RetrievalEvent] = []

    for provider_name, provider, degraded in (
        (primary_name, primary, False),
        (secondary_name, secondary, True),
    ):
        for attempt in range(1, policy.attempts_per_provider + 1):
            try:
                return WeatherRetrieval(provider_name, provider(), degraded, tuple(events))
            except ProviderConfigurationError:
                raise
            except ProviderError as error:
                if not _transient(error):
                    raise ProviderConfigurationError(str(error), status_code=error.status_code) from error
                remaining = policy.total_budget_seconds - (clock() - started_at)
                if attempt == policy.attempts_per_provider or remaining <= 0:
                    events.append(RetrievalEvent(provider_name, attempt, error.status_code, str(error)))
                    break
                backoff = policy.base_backoff_seconds * (2 ** (attempt - 1))
                requested_delay = error.retry_after_seconds if error.status_code == 429 and error.retry_after_seconds is not None else backoff
                if requested_delay < 0:
                    requested_delay = 0
                if requested_delay >= remaining:
                    events.append(RetrievalEvent(provider_name, attempt, error.status_code, str(error)))
                    break
                events.append(RetrievalEvent(provider_name, attempt, error.status_code, str(error), requested_delay))
                sleep(requested_delay)

    raise WeatherRetrievalBlocked("all approved weather providers are unavailable", tuple(events))
