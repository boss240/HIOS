# Feature Pipeline Skeleton

Related issue: #10  
Source: HEDS-010 ML / AI Operations Manual and HEDS-012 Solar PV Forecasting Methodology

## Purpose

This document defines the first feature pipeline skeleton for HIOS solar PV forecasting.

## Pipeline stages

| Stage | Description | Phase 1 output |
| --- | --- | --- |
| Source retrieval | Collect weather, plant, and historical production inputs. | Provider assumptions documented. |
| Normalization | Convert provider and plant data into internal units and structures. | Normalization requirements documented. |
| Validation | Check missing values, stale inputs, and range anomalies. | QA checklist references. |
| Feature construction | Build time, weather, plant, and historical generation features. | Candidate feature groups listed. |
| Forecast execution | Run baseline or model forecast. | Model registry placeholder. |
| Post-processing | Apply bounds, units, confidence, and output metadata. | Output expectations documented. |
| Persistence | Store forecast outputs and traceability metadata. | Data ownership and schema conventions linked. |

## Candidate feature groups

- Time features: hour, date, local timezone, forecast horizon.
- Solar context: sunrise/sunset context, daylight flag, seasonal position proxies.
- Plant metadata: capacity, location, orientation/tilt when available.
- Weather: irradiance, cloud cover, temperature, wind, humidity.
- Historical production: recent measured generation, availability/outage flags where available.

## Validation requirements

- Weather data must include provider/source metadata.
- Forecast generation must fail visibly or enter degraded mode when required inputs are missing.
- Units must be explicit.
- Forecast horizon must be explicit.

## Open decisions

- Feature store requirement.
- Batch vs streaming execution.
- Schedule frequency.
- Historical production availability.
