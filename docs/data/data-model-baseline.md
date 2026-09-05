# HIOS Data Model Baseline — Sprint 1

## Core entities
- Tenant
- User
- Role / Permission
- Plant
- GenerationObservation
- WeatherObservation
- WeatherForecast
- ForecastRun
- ForecastPoint
- ForecastQualityMetric

## Minimum data quality rules
- timestamps stored in UTC
- plant timezone stored separately
- installed capacity > 0
- provider payloads traceable
- ingestion idempotent
- missing data explicitly flagged
