# Model Registry Placeholder

Related issue: #10  
Source: HEDS-010 ML / AI Operations Manual

## Purpose

This document reserves the model registry structure for HIOS forecasting models.

## Registry record fields

| Field | Purpose |
| --- | --- |
| `model_id` | Stable model identifier. |
| `model_version` | Version used for forecast traceability. |
| `model_type` | Baseline, statistical, ML, hybrid, or external. |
| `training_dataset_ref` | Reference to training data or snapshot. |
| `feature_set_ref` | Feature pipeline version or feature contract. |
| `metrics` | Evaluation results and quality metrics. |
| `status` | Proposed, candidate, active, deprecated, retired. |
| `approved_by` | Reviewer or release decision reference. |
| `approved_at` | Approval timestamp. |
| `notes` | Known limitations and assumptions. |

## Lifecycle states

- Proposed
- Candidate
- Active
- Deprecated
- Retired

## Release rule

Only an approved active model version should be used for production forecasts. Sprint 1 does not select a production model.

## Open decisions

- Registry storage location.
- Model artifact storage.
- Evaluation metric thresholds.
- Approval workflow.
