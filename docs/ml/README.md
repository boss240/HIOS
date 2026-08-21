# ML and Forecasting Foundation

Related issue: #10  
Source: HEDS-010 ML / AI Operations Manual, HEDS-011 Weather Data Provider Integration Manual, HEDS-012 Solar PV Forecasting Methodology

## Purpose

This folder captures the initial ML and solar PV forecasting foundation for HIOS Phase 1.

## Current files

- `forecasting-methodology.md`: baseline forecasting method and assumptions.
- `weather-provider-integration.md`: provider integration assumptions and source metadata.
- `model-registry.md`: model registry placeholder.
- `feature-pipeline.md`: feature pipeline skeleton.
- `ml-ops-checklist.md`: operational checklist for ML/forecasting work.
- `forecast-quality-qa.md`: QA criteria for forecast quality.

## Initial scope

The Phase 1 forecasting foundation is documentation-first. It defines traceability, quality gates, provider assumptions, and model lifecycle placeholders before production forecasting code is introduced.

## Open decisions

- Weather provider selection.
- Forecast model family and baseline algorithm.
- Training/evaluation data sources.
- Runtime scheduling and worker platform.
- Forecast quality thresholds for release acceptance.
