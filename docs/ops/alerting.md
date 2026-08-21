# Alerting Assumptions

Related issue: #15

## Alert categories

| Category | Example trigger |
| --- | --- |
| API availability | API unavailable or high error rate. |
| Forecast freshness | Forecasts stale beyond threshold. |
| Weather provider | Provider unavailable, delayed, or partial data. |
| Data quality | Required forecast or plant data missing. |
| Security/audit | Sensitive action failure or unusual access pattern. |
| CI/deployment | Main workflow failing or deployment blocked. |

## Severity guide

- Critical: customer-impacting outage or security/data-risk condition.
- High: major degraded operation or repeated provider failure.
- Medium: localized issue with workaround.
- Low: warning or trend requiring review.

## Rules

- Alerts must have an owner or triage path.
- Forecast staleness alerts must include plant/tenant context where safe.
- Provider alerts must include provider and last successful retrieval timestamp.
