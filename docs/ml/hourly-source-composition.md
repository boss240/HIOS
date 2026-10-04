# Hourly Google + Solcast composition

`compose_hourly_operational_weather` aligns Google UTC hours with complete
Solcast irradiance intervals. The existing exact-interval composer remains
available to callers that already provide matching resolutions.

Solcast documents `period` as the averaging duration, default PT30M:
https://docs.solcast.com.au/docs/section/irradiance-weather-data
GHI, DNI and DHI are averaged with duration weights, preserving irradiation
over the hour. Cloud cover, temperature and wind come from Google's hour.
No instantaneous covariates are averaged or substituted for interval means.

The requested Google hour must be exactly tiled by Solcast. Gaps, partial
boundary overlap, duplicate/overlapping/unordered rows, naive timestamps,
nonfinite/boolean values and missing required fields reject composition.
Solcast may extend beyond Google's horizon; extra intervals are not used.
UTC conversion precedes hourly-boundary validation.

Original immutable capture IDs, receipt times, optional issue times and mapping
versions must be retained by the orchestration caller. Resolution conversion
does not backdate capture receipt or invent a provider issue time. Captures
must precede the selected common forecast origin and target hours before an
operational run or as-issued evaluation is admitted.

Bounded live read verification on 2026-10-04 obtained 24 Google intervals and 97
Solcast intervals for each approved pilot. Both composed 23 complete future
hours after excluding the already-started Google interval. That check wrote
no forecasts or actuals and does not establish model accuracy.

Remaining work: read selected immutable captures with tenant ownership, attach
their lineage to forecast inputs, validate each plant's real geometry and
approved model configuration, execute and publish the model run, then compare
against independently verified actual generation.

## Selected archive reader

`load_captured_operational_weather` now reads two explicitly selected capture
UUIDs with tenant, plant and active-member filtering in a single database query.
Missing, foreign or inactive-member scope is denied. It makes no provider calls
and does not select a newer capture automatically for a historical replay.

The reader verifies each document checksum and canonical capture contract,
requires one Google and one Solcast source received no later than the common
forecast origin, and excludes intervals already started at that origin. Its
result retains capture IDs, checksums, mapping versions and original receipt /
optional issue times alongside composed hours. Unknown issue time stays null;
it is not coerced into the older NormalizedWeather schema's mandatory issue
timestamp. An explicit model input adaptation is still required.

## Candidate generation adapter

`captured_generation_preview` now calculates MODEL-001 candidate power and
energy from the composed capture inputs with explicit geometry and model
configuration. It calls the same physical feature calculation as the existing
normalized-weather path, through a separate receipt-backed availability check.
Unknown provider issue time stays null throughout provenance.

Each point retains both capture IDs, hashes, mapping versions, receipt/issue
times, field roles and the common forecast origin. It is flagged
`uncalibrated_candidate` and `air_temperature_proxy`; unknown issue time adds
`provider_issue_time_unknown`. Air temperature currently proxies cell
temperature in this baseline and is not a validated thermal model.

This pure adapter neither writes nor publishes points. Approved configuration,
real plant geometry, runtime orchestration and actuals evaluation remain
necessary. No capacities, tilt, azimuth or performance ratio are inferred for
the pilot plants when their passport/configuration is incomplete.
