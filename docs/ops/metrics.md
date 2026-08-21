# Metrics Baseline

Related issue: #15

## Metric groups

| Group | Example metrics |
| --- | --- |
| API | Request rate, error rate, latency, auth failures. |
| Forecasting | Job success/failure, duration, freshness, stale forecast count. |
| Weather provider | Retrieval success/failure, delay, missing field rate. |
| Data quality | Missing required fields, stale records, validation failures. |
| Frontend/mobile | Availability and client error trends where available. |
| Operations | CI status, deployment status, incident counts. |

## Forecast-specific metrics

- Latest forecast generation timestamp by plant.
- Forecast freshness age.
- Provider retrieval delay.
- Forecast job failure count.
- Degraded forecast count.

## Open decisions

- Metrics backend.
- Dashboard tool.
- Alert thresholds.
- Retention period.
