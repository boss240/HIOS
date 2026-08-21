# Dashboard Shell

Related issue: #11  
Source: HEDS-013 Frontend / Web Application Specification

## Purpose

The dashboard shell is the first customer-facing landing surface after sign-in.

## Layout regions

| Region | Purpose |
| --- | --- |
| Top bar | Product identity, tenant/account context, user menu. |
| Primary navigation | Dashboard, plants, forecasts, alerts, account/admin links as permitted. |
| Summary area | Portfolio-level status and forecast health. |
| Main content | Cards/tables/charts for forecast and plant information. |
| Utility area | Filters, date range, horizon selector, export or refresh actions where permitted. |

## Dashboard widgets

| Widget | Initial content |
| --- | --- |
| Portfolio forecast summary | Aggregate generation forecast by selected horizon. |
| Plant status summary | Count of plants with normal, warning, missing, or stale forecast status. |
| Forecast freshness | Latest forecast generation timestamp and stale indicators. |
| Weather provider status | Provider availability and latest input timestamp. |
| Alerts/degraded states | Missing data, provider delay, or model warning states. |

## States

- Loading: skeleton rows/cards or neutral loading indicators.
- Empty: no plants or no forecast data available.
- Degraded: provider delay, stale forecast, missing input, or partial forecast.
- Error: API failure or permission failure.

## Open decisions

- Final visual design system.
- Default forecast horizon.
- Portfolio aggregation method.
- Refresh strategy and real-time requirements.
