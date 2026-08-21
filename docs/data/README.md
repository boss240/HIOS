# Data Foundation

Related issue: #8  
Source: HEDS-005 Data Model Specification and HEDS-009 Data Operations and Data Quality Manual

## Purpose

This folder captures the first implementation-level data baseline for HIOS Phase 1.

## Initial domains

| Domain | Description | Phase 1 status |
| --- | --- | --- |
| Tenant | Customer account and access boundary | Skeleton |
| User | Person, role, and access context | Skeleton |
| Plant | Solar PV asset metadata | Skeleton |
| Forecast | Forecast output, horizon, confidence, and quality metadata | Skeleton |
| Weather input | External weather observations and forecasts | Planned |
| Audit event | Security and operational evidence | Planned |

## Current files

- `schema-conventions.md`: initial naming and schema rules.
- `data-quality-checklist.md`: first QA gates for data operations.

## Open items

- Confirm database engine and migration tool.
- Confirm retention rules for forecasts and weather inputs.
- Confirm tenant isolation model.
- Add migration placeholders after technology selection.
