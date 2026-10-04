# Bounded device PV collection

`app.deye_device_collection.collect_device_days` is the reusable orchestration
helper for one explicitly selected device and at most 31 completed UTC days.
It does not create a cloud job or enable automatic collection by itself.

Before calling it, the server job must validate active tenant membership,
the plant's verified read-only Deye binding, and the selected device's membership
in that station. Hold a collection lock for the tenant/plant/device during the
entire operation. Never select a device by a guessed name or coordinate alone.

## Binding verification

Public binding registration creates only `pending` bindings. A caller cannot
assign `verified` or `blocked` through the registration API.
`verify_deye_binding` is a server-only service accepting a binding UUID and an
approved credential reference already resolved by the server. It locks active
ownership and the binding, confirms the exact station ID in the first bounded
account page (up to 100 stations), and requires a non-empty, non-truncated list
of unique device serials returned for that station. Only then is `verified`
committed. No match on that page is insufficient evidence, even if the account
has further pages; the service fails without guessing or changing the binding.
Provider or validation failures roll back the verification transaction.

This verifies station access, not installed PV geometry, meter boundaries or
forecast accuracy. A later collection must still authenticate and confirm the
selected device's station membership. No control endpoints are called.

Provide scoped callbacks:

- `existing_capture(day)` checks the selected tenant/plant/device hash/day.
  A saved partial day is retained; it is not silently replaced or treated as full.
- `persist_capture(day, body)` calls `store_device_solar_capture` with that same
  scope and an aware receipt time. It must raise on failed validation or storage.

The helper authenticates only when a day needs collection and reuses one token.
The first failed lookup, authentication, read or save stops the loop. Outcomes
contain only day, status and exception class, never response bodies, native IDs,
credentials or tokens. A failed run must be surfaced as failed by its caller;
earlier successful captures remain stored.

Stored device PV is separate from verified plant AC actuals. This collector
does not establish forecast accuracy or full station measurement coverage.

`app.deye_device_collection_service.collect_bound_device` provides the server
adapter: it locks the active membership, plant and verified binding, serializes
collection with a transaction advisory lock, and checks device membership in the
bound station before reading missing days. A truncated device list is rejected.
It stores through the canonical validated capture store. No device IDs are logged.

The manual job entrypoint is `python -m app.deye_device_capture_job`.
Configure server-only `HIOS_DEYE_CAPTURE_SCOPE` as a JSON list of one or two
objects with `plantId`, `bindingId`, `deviceSerial`; keep native device IDs in
secret references. Set `HIOS_DEYE_CAPTURE_START_UTC` and
`HIOS_DEYE_CAPTURE_END_UTC` to explicit completed calendar dates.
Also supply `DATABASE_URL`, `HIOS_CAPTURE_SUBJECT`, `HIOS_CAPTURE_TENANT` and
the existing Deye credential environment variables through server secrets.
Exit codes: 0 completed/skipped, 1 collection failure, 2 configuration failure.
Use a manual Azure job with retry limit zero; do not add a recurring schedule
until a successful scoped run and its persisted evidence have been verified.

Deployment remains pending production binding/device scope verification.
Do not schedule retries against unchanged rejected Deye credentials.
