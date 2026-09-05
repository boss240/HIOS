# HIOS System Context — Sprint 1 Baseline

## Primary actors
- Customer / Plant Owner
- Customer Administrator
- HIOS Administrator
- Support / Operations
- Weather Data Providers

## Core logical components
1. Web Application
2. Mobile Application
3. Backend API
4. Data Platform
5. Forecasting / ML Layer
6. Admin / Backoffice
7. Observability / Operations

## External dependencies
- Weather providers
- Notification providers
- Optional billing provider
- Optional external energy integrations

## Trust boundaries
- Public client ↔ API gateway
- API ↔ internal services
- Services ↔ databases/storage
- HIOS ↔ external providers
- Admin plane ↔ production data plane
