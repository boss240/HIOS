# Weather provider assumptions

Related issue: #10. Source: HEDS-011 WPROV-001–008, APIW-001–006,
WMAP-001–012, NORM-001–010, QS-001–008, SLA-W-001–008 and COST-W-001–008.
[Source coverage](../../sprint-02/SOURCES.md).

## Selected provider architecture

The approved target architecture has three distinct provider roles. It documents
the intended production contour, but does not enable a production adapter,
credential, scheduler or network request.

| Provider | Approved role | Use boundary |
| --- | --- | --- |
| Google Maps Platform Weather API | Operational weather covariates: temperature, cloud, wind, precipitation and alerts | Captured for each controlled run; never used as an irradiance substitute |
| Solcast | Primary operational solar-irradiance input: GHI, DNI, DHI and, where configured, GTI | Required by MODEL-001 before a forecast can publish |
| OpenWeather Solar Irradiance | Historical issued-forecast data for training and independent backtest | Offline evaluation input only; not a runtime fallback or live publication source |

Google's hourly forecast supplies up to 240 hours, which covers the proposed
24–48 hour day-ahead horizon. Solcast is the selected irradiance provider for
the same target intervals. The Google and Solcast accounts, restricted keys or
OAuth identities, quotas, budgets and named owners remain deployment
configuration; no credential is stored here or used by tests.

Google Weather offers temperature, precipitation, wind, humidity, pressure,
visibility and cloud cover. Its documented product does not provide GHI, DNI or
DHI. Solcast supplies the required irradiance fields. Do not silently substitute
Google cloud cover for irradiance or substitute OpenWeather historical data into
a live forecast run.

`app/weather_provider_roles.py` encodes these three roles as a fixed, testable
registry. It accepts Google plus Solcast for a future live forecast path and
rejects Google as an irradiance source or OpenWeather Solar as a live source.
It does not contain an HTTP client, credential, quota or automatic request.

Google's hourly history is limited to 24 hours and is not an archive of what a
forecast said at an earlier origin. From first enablement, archive each accepted
Google response with `retrieved_at_utc`, request parameters, response checksum,
valid intervals and mapping version. This creates forward-looking as-issued
evidence; it does not reconstruct prior forecast history or replace a frozen
historical holdout.

Primary WPROV-001 and secondary WPROV-002 remain roles. Google and Solcast are
the designated field-level primary sources. A live Solcast-compatible secondary
source remains unselected; OpenWeather is intentionally excluded from automatic
operational failover until its live data, units, timing and quality are separately
validated. Regional/tertiary sources may be added after validation. Reanalysis WPROV-006
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

| Google capability | Sprint 2 use | Limitation / gate |
| --- | --- | --- |
| Hourly forecast, max 240 hours | Temperature, cloud, wind and other supported covariates | Snapshot every accepted response; no documented issue timestamp means retrieval time is not forecast issue time |
| Hourly history, max 24 hours | Recent operational diagnostics only | Not suitable for training or historical holdout reconstruction |
| Current conditions and alerts | Operations context | Not a replacement for forecast inputs |
| No documented GHI/DNI/DHI | None | Solcast supplies these required fields; Google alone remains insufficient |

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
The normalizer rejects a provider issue time later than its retrieval time; this
prevents an impossible as-issued lineage record from entering feature assembly.

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

Open owners: Data Ops configures Google and Solcast quotas/TTLs and selects a
live secondary irradiance source; Product validates Google, Solcast and
OpenWeather usage rights and budget; ML Engineering validates transformations,
the historical backtest split and any future irradiance derivation.

The application configuration boundary is implemented in
`app/weather_provider_credentials.py`. It accepts only
`GOOGLE_WEATHER_API_KEY` and `SOLCAST_API_KEY` for the operational contour,
keeps their values out of object representations, and rejects missing or blank
values before any adapter can make a request. It intentionally does not load an
OpenWeather key for a live forecast path.
