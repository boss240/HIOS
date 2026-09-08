# Provider failover

Related issue: #10. Source: HEDS-011 FB-001–008 and WPI-001–008;
HEDS-010 MLI-001–004; HEDS-012 CONF-001–008.
[Source coverage](../../sprint-02/SOURCES.md).

## Routing proposal

| Condition / source rule | Action | Publication |
| --- | --- | --- |
| Timeout / 5xx / outage, FB-001 | Bounded retry then validated secondary | Degraded with provider identity |
| 429, FB-002 | Honor Retry-After within deadline; urgent job uses secondary | Degraded; log quota reason |
| Missing intervals/fields, FB-003 | Compatible secondary/regional interval fill | Degraded with per-field/interval lineage |
| Low quality, FB-004 | Review/reweight or switch under approved threshold | Flag quality; no invented score |
| Budget/quota, FB-005 | Throttle non-critical jobs or policy-approved cheaper source | Track cost and routing |
| Historical failure, FB-006 | Isolated alternative backfill or approved manual import | Never silently promote to live |
| All live sources unusable, FB-007 | Incident-controlled last usable forecast | Stale warning; otherwise blocked |
| Material divergence, FB-008 | Compare inputs and lower quality pending review | Flag; block if plausibility fails |
| 401/403 or incompatible schema | Stop affected adapter; alert owner | Valid secondary only; no blind retry |

Secondary data must pass the same units, spatial mapping, interval, freshness and
as-of gates as primary data. Preserve source versions at the filled interval/field
level. No ensemble is implemented in this slice.

Google is the selected source for general weather covariates and Solcast is the
selected source for GHI/DNI/DHI in the target operational contour. OpenWeather
Solar is reserved for historical issued-forecast training and independent
backtests; it is not an automatic runtime fallback. Add a live fallback only
after its irradiance fields, issue-time semantics, quality and contractual rights
have passed the same validation gates as Solcast.

Proposal for initial adapter testing: total request budget 30 seconds per job,
at most 3 attempts per provider, exponential backoff with jitter, and no retry past
the job deadline. These are engineering defaults pending vendor cadence/quotas.
An HTTP Retry-After beyond the remaining budget schedules later recovery and does
not trigger an immediate retry loop.

Circuit proposal: open after 3 consecutive transient failed jobs; wait 5 minutes
then allow one half-open probe. A fully validated probe closes the circuit;
failure reopens it. Explicit configuration/auth/schema faults require operator
repair. State is scoped to provider/product/environment, with bounded concurrent
probes; one tenant cannot consume the entire retry budget.

## Stale forecast safety

FB-007 reuses an existing forecast for the same tenant/plant and still-covered
target intervals. Preserve its original issue, origin and generated timestamps;
record reused_from_run_id, staleness, reason and incident owner.
A reuse-age maximum must be approved for the horizon before enabling this mode.
Until configured, last-forecast reuse is disabled. Never shift old valid times,
copy yesterday's curve to today, relabel stale output as fresh, or fabricate zeros.
If no compatible usable forecast exists, publish blocked status without values.

Recovery requires a fresh complete payload, successful probe and monitored
resumption; compare against fallback for material divergence. Do not overwrite
previous runs or erase the incident. SRE/Data Ops owns routing; ML Ops reviews
quality impact; Incident Commander controls emergency reuse.
