# Weather Provider Integration

Related issue: #10  
Source: HEDS-011 Weather Data Provider Integration Manual

## Purpose

This document captures the initial weather provider assumptions for HIOS forecasting.

## Provider responsibilities

A weather provider integration should supply weather data needed for solar PV forecasting. Exact provider selection is pending.

## Required metadata

Every provider payload or normalized weather record should preserve:

- provider name
- provider endpoint or product name
- retrieval timestamp
- forecast issue timestamp when available
- location reference
- forecast horizon
- units
- raw provider status or error state when applicable

## Candidate weather fields

| Field | Why it matters |
| --- | --- |
| Global horizontal irradiance | Primary solar generation driver when available. |
| Direct normal irradiance | Useful for refined PV modeling when available. |
| Diffuse horizontal irradiance | Useful for cloud and sky-condition modeling. |
| Cloud cover | Proxy for irradiance when direct values are unavailable. |
| Temperature | Impacts panel efficiency. |
| Wind speed | May influence module temperature assumptions. |
| Humidity / precipitation | Supports weather-state context and QA review. |

## Failure and degraded modes

- If provider data is delayed, record the delay and avoid silent substitution.
- If a field is missing, mark the normalized value as unavailable rather than inferred unless an explicit rule exists.
- If provider service is unavailable, forecasting should produce a documented degraded-mode result or skip generation with a traceable error.

## Open decisions

- Primary weather provider.
- Backup provider strategy.
- Provider quota and rate limit handling.
- Normalization schema.
- Raw payload retention policy.
