# Weather provider assumptions

Related issue: #10. Source: HEDS-011 WPROV-001–008, APIW-001–006,
WMAP-001–012, NORM-001–010, QS-001–008, SLA-W-001–008 and COST-W-001–008.
[Source coverage](../../sprint-02/SOURCES.md).

## Provider roles and unresolved configuration

Primary WPROV-001 and secondary WPROV-002 are roles, not vendor names.
Regional/tertiary sources may be added after validation. Reanalysis WPROV-006
is for historical reconstruction; manual WPROV-007 imports require review and
must not silently enter live ingestion. A status endpoint is supporting metadata,
not proof that a payload is usable.

Before an adapter is enabled, record provider/product/version, endpoint, allowed
locations/horizons, issue cadence, timezone, field mapping version, request deadline,
freshness TTL, retry budget, quotas, owner and credential reference. Verify storage,
training and redistribution rights against the supplier's actual terms. Secrets
stay outside source control and logs. No live or paid calls are enabled by this PR.

HEDS APIW paths describe logical capabilities; do not assume a supplier literally
implements /forecast or /metadata. Map each capability to documented vendor APIs.

## Canonical weather contract proposal

| Source fields | Canonical fields / units | Readiness |
| --- | --- | --- |
| GHI | irradiance_global_wm2, W/m² | Required |
| DNI / DHI | irradiance_direct_wm2 / irradiance_diffuse_wm2, W/m² | Record absence and chosen decomposition |
| Cloud | cloud_cover_pct, 0–100% | Required by this baseline |
| Temperature | temperature_c, °C | Required; Kelvin conversion is explicit |
| Wind | wind_speed_ms, m/s | Optional with model assumption; km/h divided by 3.6 |
| Direction / humidity / precipitation | wind_direction_deg / relative_humidity_pct / precipitation_mm | Optional; preserve nulls |
| Condition | condition_code_normalized | Versioned provider mapping |
| Issue / valid time | provider_issued_at_utc / valid_at_utc | Required |

Also preserve requested and returned coordinates, original timezone/units,
retrieved_at_utc, ingestion_run_id, payload checksum/reference, provider/product,
mapping version, target interval start/end, aggregation semantics and quality flags.
Unknown units, naive/ambiguous timestamps, impossible values and schema changes
are quarantined. Accumulated irradiation must be converted using its interval;
it is not instantaneous or average irradiance without that conversion.
Do not reject irradiance solely because it exceeds 1000 W/m².

Normalize in UTC and preserve original plant coordinates (NORM-001–003).
Do not invent sub-hourly detail from hourly data. Flag missing coverage and preserve
interval-level provenance when filling gaps (NORM-004–009).
Backfill and reanalysis remain separate from live input versions (NORM-010).

## Readiness, costs and retention

Required interval coverage is complete for normal publication; partial runs are
degraded only under an approved missing-data policy. Unknown provider issue time
blocks operational freshness validation. TTL and latency thresholds must be set
per selected product; a freshly retrieved old forecast is still stale.

Measure coverage, latency, freshness, stability, divergence, forecast impact,
cost efficiency and trust (QS-001–008). Composite weighting and thresholds are
pending calibration; a missing score is unknown, not 100. The source availability
target >=99.0% (SLA-W-001) is a planning target, not an achieved supplier SLA.

Track requests and costs by tenant/plant/environment; cap non-production traffic,
alert before quota exhaustion, estimate fallback cost and review bulk downloads.
Use [failover rules](provider-failover.md). Follow the existing
[retention policy](../data/retention-policy.md): raw weather 90d and reproducible
forecast lineage 730d, subject to approved supplier rights and holds. No purge is
implemented here; normalized snapshots must outlive raw expiry where needed.

Open owners: Data Ops selects primary/secondary and TTL/quotas; Product validates
usage rights and budget; ML Engineering validates field transformations.
