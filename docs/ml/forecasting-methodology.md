# Forecasting Methodology Baseline

Related issue: #10  
Source: HEDS-012 Solar PV Forecasting Methodology

## Purpose

This document defines the first implementation baseline for solar PV generation forecasting in HIOS.

## Forecast objective

Produce forecast outputs for solar PV plants with enough traceability to support customer operations, QA review, and later model improvement.

## Initial forecast horizons

| Horizon | Purpose | Phase 1 status |
| --- | --- | --- |
| Intraday | Operational visibility and short-term adjustments | Planned |
| Day-ahead | Planning and customer-facing forecast views | Planned |
| Multi-day | Trend and planning context | Later phase |

## Input categories

- Plant metadata: capacity, location, orientation/tilt if available.
- Weather forecast: irradiance, cloud cover, temperature, wind, humidity where available.
- Historical production: measured generation, outages, curtailment indicators where available.
- Calendar/time: timestamp, local time, sunrise/sunset-derived context where available.

## Output expectations

Forecast outputs should include:

- plant id
- forecast generation timestamp
- valid time or interval
- forecast horizon
- predicted generation
- unit of measure
- model or method version
- source weather provider reference
- quality/confidence metadata when available

## Baseline modeling approach

The initial implementation may start with a simple deterministic or statistical baseline before advanced ML models are introduced. Any baseline must remain traceable and comparable against future models.

## Open decisions

- Target unit and aggregation interval.
- Baseline model family.
- Accuracy metrics and acceptance thresholds.
- Handling of missing provider data.
- Handling of plant outages and curtailment.
