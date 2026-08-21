# Forecast Views

Related issue: #11  
Source: HEDS-013 Frontend / Web Application Specification and HEDS-012 Solar PV Forecasting Methodology

## Forecast chart view

### Purpose

Show forecasted generation over a selected time horizon in a way that supports quick operational interpretation.

### Chart requirements

- Time-based x-axis.
- Generation value y-axis with explicit unit.
- Selected horizon visible.
- Forecast generation timestamp visible.
- Stale/degraded indicators visible when applicable.
- Confidence or quality metadata visible when available.

### Candidate series

- Forecast generation.
- Actual generation where available.
- Confidence band where available.
- Capacity/reference line where useful.

## Forecast table view

### Purpose

Provide precise forecast values and traceability metadata.

### Columns

| Column | Purpose |
| --- | --- |
| Valid time | Forecast target timestamp or interval. |
| Predicted generation | Forecast value and unit. |
| Horizon | Forecast horizon. |
| Model/version | Forecast traceability. |
| Weather provider | Input source traceability. |
| Quality/confidence | Forecast quality context when available. |
| Status | Normal, degraded, stale, missing input, warning. |

## Interactions

- Select horizon.
- Switch chart/table views.
- Filter by date/time range.
- Refresh where permitted.
- Export where permitted in later phases.

## Open decisions

- Charting library.
- Default aggregation interval.
- Exact unit convention.
- Confidence display design.
