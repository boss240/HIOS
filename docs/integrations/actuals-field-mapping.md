# Actual-generation field mapping contract

Related issue: #10 (EPIC-005); sprint tracking: #22. This contract is used
after a provider's read-only access, per-plant scope and native field response
have been verified. It contains no provider credentials, native plant IDs,
device IDs or raw responses.

## Required mapping record

Each mapping has a provider and immutable mapping version, source IANA timezone,
native observed/interval-end field names, and at least one measured field.
Power uses `W` or `kW`; energy uses `Wh` or `kWh` and is explicitly labelled as
`interval` or `cumulative`. A status field is optional.

`app/actuals_field_mapping.py` validates this record and converts mapped values
to canonical kW/kWh. It preserves the energy semantics instead of treating a
cumulative counter as interval energy. The mapping has no HTTP client and cannot
create an `InverterCloudBinding`, store an actual or enable a provider.

Migration `0010_actual_energy_semantics.sql` retains that explicit semantic
label with every later normalized energy observation. A row with energy requires
either `interval` or `cumulative`; a row without energy cannot carry a label.
This schema change does not authorize any provider row or determine which Deye
field has either meaning.

`app/actuals_row_normalization.py` is the subsequent pure conversion boundary.
It accepts a row only through an already-approved mapping, requires every mapped
field to be present, converts W/Wh into kW/kWh and constructs an unstored
`ActualGenerationObservation`. The caller must separately resolve timestamp
format, timezone and interval boundary; the converter cannot infer them, call a
provider, retain raw payloads or write a snapshot.

## Deye pilot gate

For each pilot, record the actual Deye field names only in the restricted
operations evidence store after native discovery. Verify timestamp timezone,
interval boundary, AC power measurement boundary, energy semantics, status codes,
missing values and corrections against a short read-only sample. The mapping
version must be retained with every later actual-generation snapshot.
