# Forecast Quality QA Criteria

Related issue: #10  
Source: HEDS-012 Solar PV Forecasting Methodology and HEDS-018 QA and Test Strategy

## Purpose

This document defines the initial QA criteria for HIOS solar PV forecast quality.

## Required QA dimensions

| Dimension | Check |
| --- | --- |
| Traceability | Forecast output links to model/version, provider, and generation timestamp. |
| Freshness | Forecast generation and valid interval are explicit. |
| Completeness | Required plant, weather, and forecast fields are present. |
| Plausibility | Forecast values are non-negative and bounded by plant capacity assumptions. |
| Missing data | Missing weather or production inputs are visible and handled explicitly. |
| Provider reliability | Provider errors, delays, and degraded modes are recorded. |
| Accuracy | Metric targets are defined before release acceptance. |

## Candidate accuracy metrics

- MAE: mean absolute error.
- RMSE: root mean squared error.
- MAPE or normalized error where appropriate.
- Bias by horizon or plant segment.

## Acceptance baseline

Sprint 1 does not define production accuracy thresholds. Before forecasting MVP release, the team must define:

- evaluation dataset
- forecast horizon targets
- acceptable error thresholds
- comparison baseline
- evidence format for QA sign-off

## Open risks

- Weather provider data quality may dominate forecast quality.
- Historical production data may be incomplete or unavailable.
- Outages and curtailment may distort model evaluation if not labeled.
