# Push Notification Assumptions

Related issue: #12  
Source: HEDS-014 Mobile Application Specification

## Notification categories

| Category | Trigger |
| --- | --- |
| Forecast stale | Forecast has not refreshed within accepted freshness window. |
| Provider degraded | Weather provider unavailable, delayed, or partially missing data. |
| Plant warning | Plant forecast status enters warning/degraded state. |
| System notice | Operational or maintenance notice relevant to the user. |

## Payload requirements

- Notification category.
- Tenant/account context where safe.
- Plant id/name where safe.
- Severity.
- Timestamp.
- Deep link target.

## Safety rules

- Do not include secrets or sensitive diagnostic details in notification text.
- Respect user and tenant notification settings.
- Record notification delivery intent for audit/diagnostic review when required.

## Open decisions

- Push provider.
- User preference model.
- Quiet hours and escalation behavior.
- Retry and delivery evidence requirements.
