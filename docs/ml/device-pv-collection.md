# Bounded device PV collection

`app.deye_device_collection.collect_device_days` is the reusable orchestration
helper for one explicitly selected device and at most 31 completed UTC days.
It does not create a cloud job or enable automatic collection by itself.

Before calling it, the server job must validate active tenant membership,
the plant's verified read-only Deye binding, and the selected device's membership
in that station. Hold a collection lock for the tenant/plant/device during the
entire operation. Never select a device by a guessed name or coordinate alone.

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

Deployment remains pending the cloud job entrypoint and production scope setup.
Do not schedule retries against unchanged rejected Deye credentials.
