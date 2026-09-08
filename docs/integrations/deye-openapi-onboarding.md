# Deye OpenAPI onboarding for the controlled pilot

Related issue: #10 (EPIC-005); selected plants:
[Deye pilot register](deye-pilot-register.md).

This runbook is based on Deye's published API v1 documentation and its official
Python examples, reviewed on 2026-09-09. It defines the only API surface HIOS
may use for the non-production, read-only pilot. It does not create a Deye
application, request a token, call an API or store a secret.

## Official integration facts

- The documented European API base is `https://eu1-developer.deyecloud.com`.
- Deye requires an application with an AppId and AppSecret before a token can
  be obtained.
- The official sample uses the token endpoint with a Deye account and an
  optional business `companyId`; account information can provide that company
  relationship.
- Station discovery is available through `POST /v1.0/station/list` and
  `POST /v1.0/station/listWithDevice`.
- Station history is available through `POST /v1.0/station/history`; the
  sample documents frame, day, month and year granularities. A frame request
  returns power-related values; day requests support at most 31 days and month
  requests at most 12 months.

## Read-only allowlist

The approved pilot request sequence is:

1. `POST /v1.0/account/info` — confirm the business account context.
2. `POST /v1.0/account/token` — obtain a short-lived access token through the
   supplier-approved application flow.
3. `POST /v1.0/station/list` — discover native IDs and select only the two
   registered pilot plants.
4. `POST /v1.0/station/device` — map devices under the selected native IDs.
5. `POST /v1.0/station/history` — retrieve bounded historical intervals.
6. `POST /v1.0/station/history/power` and `POST /v1.0/station/latest` — only
   when needed to establish interval semantics and current-data reconciliation.
7. `POST /v1.0/station/alertList` — only for outage and data-quality context.

All requests must be POST over TLS, use an explicit allowlist, include the
selected native station ID, and be written to an immutable audit record without
secret values. The initial historical request should cover one closed UTC day
per plant. Expand the window only after field mapping and reconciliation pass.

## Explicitly blocked API classes

HIOS must reject every endpoint outside the allowlist, including:

- `/v1.0/station/create`;
- `/v1.0/device/addLogger`, `/v1.0/device/deleteLogger` and
  `/v1.0/device/register`;
- every `/v1.0/order/*` control endpoint;
- every write-capable configuration endpoint;
- `/v1.0/strategy/dynamicControl` and related strategy operations.

No worker, scheduler or CI job may hold account passwords. Store the supplier
application credentials and any token only in the approved secret manager, and
retain in HIOS only a secret reference. A token response must be redacted before
logging or persistence.

## Pilot acceptance before ingestion

For each selected plant, retain the native station ID, mapping version and a
small source-evidence record. Verify UTC conversion, frame interval, AC versus
DC/meter boundary, energy units, missing readings, corrections and outage
flags. The two plants remain isolated in separate tenant-and-plant scopes until
these checks and the existing enablement gate pass.

## Sources

- [Deye OpenAPI documentation](https://developer.deyecloud.com/api)
- [Deye API v1 Python samples](https://github.com/DeyeCloudDevelopers/deye-openapi-client-sample-code)
