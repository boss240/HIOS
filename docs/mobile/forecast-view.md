# Mobile Forecast View

Related issue: #12

## View goals

The mobile forecast view should give a compact operational answer: current forecast, freshness, plant context, and warning state.

## Main components

| Component | Purpose |
| --- | --- |
| Plant header | Plant name, status, capacity/location summary. |
| Forecast card | Current selected horizon and predicted generation. |
| Mini chart | Time-series forecast preview. |
| Detail table | Timestamped forecast values and status. |
| Freshness indicator | Generation time and stale/degraded state. |
| Provider context | Weather provider and last input timestamp. |

## Required states

- Loading.
- Empty forecast.
- Stale forecast.
- Provider degraded.
- Access denied.
- Offline cached state.

## Open decisions

- Chart component and interaction model.
- Default forecast horizon.
- Offline cache retention.
