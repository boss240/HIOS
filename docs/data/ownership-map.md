# Data Ownership Map

Related issue: #8  
Source: HEDS-005 Data Model Specification and HEDS-009 Data Operations and Data Quality Manual

## Ownership baseline

| Data area | Owner boundary | Notes |
| --- | --- | --- |
| Tenant | Identity and admin | Defines customer account boundary. |
| User | Identity and access | Must support roles and audit requirements. |
| Plant | Plant registry | Core solar PV asset metadata. |
| Forecast | Forecasting | Must preserve model/version and validity metadata. |
| Weather input | Weather integration | Must preserve provider/source metadata. |
| Billing state | Billing and entitlements | Controls commercial access logic. |
| Audit event | Security and operations | Required for sensitive actions and compliance evidence. |

## Stewardship rules

- Each tenant-scoped record must be traceable to a tenant.
- Forecast outputs must be traceable to input source and model/version.
- Sensitive changes must be auditable.
- Data quality exceptions must be documented before release acceptance.

## Open decisions

- Final ownership after runtime architecture is selected.
- Data retention and archival policy.
- Export format for handover and audit evidence.
