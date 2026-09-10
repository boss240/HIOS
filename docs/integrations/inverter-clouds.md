# Inverter-cloud integrations — first wave

Related issue: #10 (EPIC-005); sprint tracking: #22.

HIOS will ingest inverter-cloud data through read-only, tenant-and-plant-scoped
adapters. This first wave defines the ten target platforms and the single
canonical telemetry contract. It does not call any provider, retain a credential,
authorize a customer, create an API application, command a device or run a
background poller.

## Provider register

| Provider / cloud | Access route | Expected data | Readiness |
| --- | --- | --- | --- |
| Deye Cloud | DeyeCloud OpenAPI / partner access | Plant, inverter, generation, status | Contract and owner consent required |
| SolarEdge ONE | OAuth 2.0 developer application | Site, production, consumption, storage, device telemetry | Developer registration and owner grant required |
| SMA Sunny Portal / ennexOS | OAuth 2.0 plus owner consent | Plant/device measurements, events and logs | Contract, client credentials and consent required |
| Fronius Solar.web | Query API key | System/device, real-time and historical data, alerts | Business contract and key required |
| Huawei FusionSolar | Partner northbound API | Device KPIs, alarms and history | Partner approval and credentials required |
| GoodWe SEMS | Open platform client credentials | Plant/device real-time and historical measurements, alarms | Application registration required |
| Growatt ShineServer | Partner/API access to verify | Plant and generation data | No adapter until official access terms and endpoint contract are confirmed |
| Sungrow iSolarCloud | OAuth 2.0 developer portal | Plant/device statistics, monitoring and MQTT live data | Developer registration and owner grant required |
| SolisCloud | Owner HMAC or third-party OAuth 2.0 | Plant/device telemetry, history and real-time forwarding | Sales qualification and credentials required |
| Victron VRM | JWT access token | Installation telemetry, reports and alarms | Owner access token and scope review required |

The register reflects publicly documented access paths as reviewed on 2026-09-09:
[Deye](https://developer.deyecloud.com/),
[SolarEdge](https://developer.solaredge.com/),
[SMA](https://developer.sma.de/sma-apis),
[Fronius](https://www.fronius.com/en/solar-energy/solar-solutions/energy-management/solarweb-query-api),
[Huawei](https://support.huawei.com/enterprise/en/doc/EDOC1100307213/ec40b249/device-convergence-data-interface),
[GoodWe](https://developers.we.goodwe.com/docs/main/overview),
[Growatt](https://openapi.growatt.com/),
[Sungrow](https://developer-api.isolarcloud.com/),
[Solis](https://developer.soliscloud.com/guide/), and
[Victron](https://vrm-api-docs.victronenergy.com/).

## Adapter contract and controls

Every adapter returns only canonical telemetry: UTC observation and retrieval
times; AC power; energy; device status; provider/device identifiers; source
reference; and a versioned mapping. Adapter input contains tenant/plant scope,
external plant ID, a secret-manager reference and the consent-record reference.
Secret values, passwords and owner tokens never enter Git, logs, outcomes or
database error text.

The [actual-generation field mapping contract](actuals-field-mapping.md)
requires explicit source timezone, units and energy semantics before an adapter
can convert a provider response into canonical measurements.

Connections are read-only. Remote control, inverter configuration, firmware
updates, dispatch, account changes and device onboarding are excluded. A provider
must fail closed on missing consent, invalid credentials, missing plant scope,
schema drift, non-UTC timestamps or negative energy values.

## Enablement gate per provider and plant

1. Register HIOS as an application or complete the supplier contract.
2. Obtain the system owner’s explicit, revocable consent where the supplier
   requires it.
3. Store only the credential reference and grant the least read-only scope.
4. Map the provider fields and intervals to the canonical contract; retain a
   raw evidence checksum and versioned mapping.
5. Run a tenant-isolation and historical-reconciliation test on one non-production
   plant.
6. Approve polling cadence, quota, retention, incident owner and recovery rules.

Until all six gates pass, the adapter remains unavailable. The controlled forecast
worker and production scheduler stay disabled.

## Forecasting use

Telemetry is the factual-generation input needed for MODEL-001 calibration and
evaluation. Align each accepted record with the measurement boundary, plant,
exact UTC interval and meter semantics before it enters a training or holdout
dataset. Provider cloud values are not automatically treated as ground truth;
missing intervals, corrected values and device outages must remain visible.

## Active Deye pilot scope

The first selected Deye Cloud plants are recorded in the
[Deye pilot register](deye-pilot-register.md). Their selection authorizes only
the controlled, read-only pilot preparation described there; it does not bypass
the per-plant enablement gate or activate a connection.
