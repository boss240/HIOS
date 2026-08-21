# Role-Aware Navigation

Related issue: #11  
Source: HEDS-013 Frontend / Web Application Specification and HEDS-006 Security Architecture

## Purpose

This document defines the initial frontend navigation model by role category.

## Role categories

| Role category | Navigation access |
| --- | --- |
| Customer user | Dashboard, plants, forecasts, account/profile. |
| Customer admin | Customer user access plus tenant/account settings where permitted. |
| Support operator | Tenant search/context, dashboard diagnostics, plant/forecast diagnostics. |
| System admin | Platform configuration and admin/backoffice links. |

## Navigation items

| Item | Customer user | Customer admin | Support operator | System admin |
| --- | --- | --- | --- | --- |
| Dashboard | Yes | Yes | Yes | Yes |
| Plants | Yes | Yes | Yes | Yes |
| Forecasts | Yes | Yes | Yes | Yes |
| Alerts | Yes | Yes | Yes | Yes |
| Account settings | Limited | Yes | No | No |
| Tenant diagnostics | No | No | Yes | Yes |
| Admin/backoffice | No | Limited/link | Yes | Yes |
| Billing/entitlements | No | Limited | Limited | Yes |

## Security expectations

- Navigation visibility is not authorization by itself.
- API authorization must enforce access even if UI hides controls.
- Role-restricted actions must be auditable where sensitive.
- Tenant context switching must be explicit for support/system roles.

## Open decisions

- Final permission model.
- Tenant switching UX.
- Admin/backoffice separation vs shared shell.
