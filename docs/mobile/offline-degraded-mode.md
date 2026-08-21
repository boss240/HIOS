# Offline and Degraded Mode

Related issue: #12

## Offline behavior

- Show last cached plant and forecast data when available.
- Clearly label cached data with last updated timestamp.
- Disable actions that require live server confirmation.
- Queue only safe local preferences if the final implementation supports it.

## Degraded behavior

| Condition | User-facing behavior |
| --- | --- |
| Forecast stale | Show stale label and last generation timestamp. |
| Provider delayed | Show provider warning and last successful input timestamp. |
| Partial forecast | Mark incomplete intervals and show available data. |
| API unavailable | Show error state and retry option. |

## Evidence requirements

- Degraded states should be testable in QA.
- Forecast freshness and provider status must be visible.
- User must not confuse cached/stale data for live forecast data.
