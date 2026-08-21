# Frontend User Flows

Related issue: #11  
Source: HEDS-013 Frontend / Web Application Specification

## Primary user flows

### Customer operator: review forecast status

1. Sign in.
2. Land on dashboard.
3. Review portfolio forecast summary.
4. Open plant detail.
5. Inspect forecast chart and table.
6. Review freshness, horizon, and confidence metadata.

### Customer operator: investigate plant forecast

1. Open plant list.
2. Filter or search for a plant.
3. Open plant detail.
4. Compare current forecast with recent production context when available.
5. Review weather/provider freshness indicators.

### Customer admin: review access and tenant context

1. Sign in with admin-capable role.
2. Open account or tenant area.
3. Review user/role summary.
4. Follow link to admin/backoffice scope when deeper operations are required.

### Support or platform user: diagnose customer issue

1. Sign in with elevated role.
2. Select tenant/customer context.
3. Review dashboard and plant detail status.
4. Check forecast freshness and provider warning states.
5. Link findings to support/admin workflow.

## Flow requirements

- Tenant context must be visible or inferable on protected screens.
- Forecast freshness must be visible where forecasts are shown.
- Empty, loading, degraded, and error states must be designed for each major view.
- Role-restricted navigation items must not expose unauthorized actions.
