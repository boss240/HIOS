# Deye Cloud telemetry: read-only evidence gateway

HIOS uses the official Deye Cloud API v1 only to discover stations and inspect
measured generation needed to calibrate forecasts. The integration calls a
short allow-list: account token, station list, station device, station latest,
and station history. It contains no endpoint for changing inverter power,
battery settings, operating mode or schedules.

## First controlled reading

The dashboard request `POST /dashboard/deye/stations/{station_id}/telemetry-audit`
requires Basic dashboard access, `confirmReadOnly: true`, and a past UTC date.
It reads one station-history frame day and returns only a quality summary:
sample count, timestamp cadence, numeric-field counts and schema flags. Raw
Deye rows, access tokens and credentials are not returned or stored.

A successful audit is evidence for the next separate mapping decision. Before
HIOS persists actual generation, Data Ops must validate Deye field units,
interval semantics and timezone against a protected sample, then record a
versioned mapping under the actual-generation contract.

The official Deye sample documents the frame history request as station history
with `granularity: 1` and a `yyyy-MM-dd` start date. Historical daily, monthly
and yearly readings use the same read-only history resource at other
granularities.

## Explicit exclusion

Deye Cloud also publishes device-control and strategy examples. HIOS does not
expose, import or invoke them. Any future dispatch function requires an
independent operational policy, limits, audit log, emergency stop, operator
roles and a separate authorization decision.

Sources: [Deye Developer Portal](https://developer.deyecloud.com/start) and
[official API v1 Python samples](https://github.com/DeyeCloudDevelopers/deye-openapi-client-sample-code).
