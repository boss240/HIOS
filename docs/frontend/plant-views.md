# Plant Views

Related issue: #11  
Source: HEDS-013 Frontend / Web Application Specification

## Plant list view

### Purpose

Allow users to scan, search, and open solar PV plants assigned to their tenant/account.

### Fields

| Field | Purpose |
| --- | --- |
| Plant name | Human-readable plant identifier. |
| Location | Operational context and forecast relevance. |
| Capacity | PV plant capacity for forecast interpretation. |
| Forecast status | Normal, stale, missing, degraded, warning. |
| Latest forecast | Latest forecast generation timestamp. |
| Provider status | Weather provider freshness or warning. |

### Controls

- Search by plant name.
- Filter by forecast status.
- Filter/sort by freshness.
- Open plant detail.

## Plant detail view

### Purpose

Provide detailed operational context for one plant and its forecast outputs.

### Sections

| Section | Content |
| --- | --- |
| Header | Plant name, status, capacity, location. |
| Forecast summary | Selected horizon and predicted generation. |
| Forecast chart/table | Time-series view and tabular details. |
| Weather context | Provider, retrieval time, input status. |
| Metadata | Plant assumptions and forecast/model version details. |
| Warnings | Stale, missing, degraded, or quality-warning states. |

## Required states

- Plant not found.
- Access denied.
- No forecast available.
- Forecast stale.
- Provider degraded.
