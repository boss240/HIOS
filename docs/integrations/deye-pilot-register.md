# Deye Cloud pilot register

Related issue: #10 (EPIC-005); sprint tracking: #22.

This register records the two user-selected Deye Cloud plants for the first
tenant-safe, read-only actuals pilot. It intentionally contains no account
credential, address, serial number, native cloud identifier, API key or device
control information.

## Selected plants

| HIOS pilot key | Deye display name | Observed operating state | Installed capacity | Intended use | Native plant ID |
| --- | --- | --- | --- | --- | --- |
| `deye-pilot-pohreby` | Погреби | Online; no alarms | 30 kWp | Actual-generation calibration and holdout evaluation | Pending verified read-only discovery |
| `deye-pilot-borshchiv` | Борщів | Online; no alarms | 30 kWp | Independent actual-generation calibration and holdout evaluation | Pending verified read-only discovery |

The operating state and capacity were observed in the Deye Cloud business
dashboard on 2026-09-09. They are operational context only, not an accepted
historical dataset or production availability commitment.

## Binding prerequisites

Before either row becomes an `InverterCloudBinding`, Data Ops must retain:

1. the owner's revocable consent reference for this exact plant;
2. the official Deye partner/API access route and a secret-manager reference;
3. the provider-native plant ID found through that approved read-only route;
4. a versioned mapping for AC power, energy, status, interval and timezone;
5. a historical reconciliation result against the agreed measurement boundary.

The source system's account password or session must never be stored in HIOS,
Git, test fixtures, logs or outcomes. The two plants remain unbound until all
prerequisites are satisfied.

## First data slice

For each plant, request or retrieve only the minimum evidence required for the
non-production pilot:

- UTC timestamp and native interval;
- AC power and interval/cumulative energy with the associated meter semantics;
- inverter/device status and outage flags;
- native source reference, retrieval timestamp and mapping version;
- coverage boundaries and corrections for the historical interval.

Use the two plants as separate series. Do not combine them before per-plant
quality checks and a tenant-isolation test pass.
