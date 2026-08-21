# BCP and Disaster Recovery Links

Related issue: #15  
Source: HEDS-019 Business Continuity and Disaster Recovery Manual

## Operational dependencies

| Area | Recovery concern |
| --- | --- |
| API | Restore service availability and contract behavior. |
| Database | Restore tenant, plant, forecast, billing, audit data. |
| Forecasting jobs | Resume scheduled forecast generation. |
| Weather provider | Detect provider outage and use degraded-mode behavior. |
| Notifications | Recover alert delivery or record delivery gap. |
| Admin/backoffice | Restore support and operational access. |

## Required future work

- Define backup frequency.
- Define restore test cadence.
- Define RPO/RTO targets.
- Define incident communication workflow.
- Define provider outage playbook.

## Sprint 1 status

This file is a placeholder link between operations planning and BCP/DR requirements. Detailed recovery runbooks are later-phase work.
