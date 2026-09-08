# Sprint 2 status and audit

Audit date: 2026-09-06. Related issue: #10.
Sources: HEDS-022 reporting, HEDS-023 acceptance_checks.
[Plan](README.md) / [acceptance](ACCEPTANCE.md) / [sources](SOURCES.md).

## Verified starting state

Repository boss240/HIOS, default branch main; local checkout was clean at bbc3439.
Fetched main 63710a1 ("Add files via upload"). PR #20 and #21 were merged.
All issues were checked: #5/#6/#7/#8/#16/#18/#19 are closed, Project 3 Done.
#10 is open; duplicate #9 is closed and absent from the board.
#11–15/#17 are open/Backlog. No Sprint 2 issue or open PR existed at kickoff.
Historical issue bodies still mention pending Sprint 1 acceptance despite closure;
this audit records live state without inventing a new sign-off.

Starting Actions on main: Documentation baseline succeeded (33991513174);
Sprint 1 baseline files failed (33991513157: liveness security missing);
Runtime integration failed (33991513103: 30 failed/3 passed, response schemas absent).
The upload replaced the implemented OpenAPI contract with a placeholder.
This change restores only docs/api/openapi.yaml from bbc3439; other uploaded
documentation is retained. This is a regression repair, not repeated Sprint 1 work.

Branch protection requires Documentation baseline, Sprint 1 baseline files and
Runtime integration, strict up-to-date checks and one approval. No protection
changes or bypass are part of this Sprint 2 change. The new Forecasting
documentation check runs on PRs/main but is not yet a required protection check.

Project 3: canonical #10 moved Backlog -> In Progress on 2026-09-06.
Sprint tracking #22 was created after checking for duplicates and added to
Project 3 as In Progress under M3 Forecasting MVP.

After PR #23 was merged, branch `feature/22-forecast-persistence` began S2-04.
It adds forward migration 0002 and a membership/plant-checked, idempotent forecast
run store. It does not add a worker, forecast API route, actuals/weather ingest or
numeric accuracy claim.

S2-04 next adds immutable, tenant-checked forecast-point publication for normal or
degraded versioned runs. Duplicate interval retries are ignored; changed predictions
must use a new run, and blocked runs cannot publish stale output. Scheduler and
worker orchestration remain pending.

S2-05 begins with an untrained deterministic MODEL-001 candidate: it requires
separate positive DC/AC capacities and versioned physical coefficients, receives
plane-of-array irradiance rather than undocumented GHI substitution, validates
solar context, clips output to the AC bound and flags night/clipping. It has no
solar-position engine, feature assembly, calibration, model registry artifact or
production activation; those remain gated by real metadata, weather and actuals.

The following S2-05 slice adds `model-001-features-v1`: an as-of-safe candidate
feature assembly with explicit plant geometry and an isotropic DNI/DHI/GHI to
POA conversion. It rejects absent DNI/DHI and weather unavailable at the forecast
origin, and produces a zero POA feature only after calculated night context. The
solar coefficients are a versioned candidate baseline, pending validation against
an approved solar library and real plant data.

The next S2-05 slice adds migration 0004 and immutable tenant/plant-scoped model
candidate metadata. A candidate can be registered once by an active tenant member;
resolution returns only an approved version in that scope. Promotion authorization,
activation, artifact storage, rollback and calibration remain explicit separate
workflows and are not inferred from candidate registration.

The next slice adds a controlled in-process MODEL-001 job. It resolves an
approved tenant/plant candidate, verifies model/configuration/input/code lineage,
builds all points before creating a run and publishes idempotently thereafter.
There is still no scheduler, network client, API route, job lock, live provider
configuration, production activation or acceptance claim.

The S2-07 scheduling slice adds an explicit UTC cadence/delay interface and
migration 0005 for renewable tenant/plant/origin/horizon job leases. Only active
tenant members can operate a lease, which prevents a concurrent worker from
running the same logical origin. No process is scheduled or started; owner,
cadence, monitoring, lock TTL, staging load evidence and acceptance remain open.

The controlled worker wrapper now claims/releases the lease around a single
MODEL-001 job and writes minimal auditable `running`, `succeeded` or `failed`
outcomes in migration 0006. Failure records contain only the exception class;
they never store provider payloads, credentials or exception messages. A real
scheduler, retry/supervision policy, monitoring/alerts, named owner, staging load
test and acceptance remain open.

The follow-up read-only operational summary reports outcome counts and published
point totals only within a tenant/plant UTC window. It does not calculate or
claim availability because expected schedules and deadlines are still unapproved.

Worker failure handling is now explicitly tested: an unapproved model records a
sanitized failed outcome and releases its lease before the original error reaches
the external supervisor.

S2-06 now has deterministic fixture-level ACC-001–005 calculations. It reports
zero eligible pairs as not evaluated and does not persist actuals, set thresholds
or claim accuracy; those actions remain blocked on a frozen real-data holdout and
ML/QA/Product approval.

S2-03 then began with a provider-independent normalizer: canonical UTC intervals,
documented units, finite/range checks and no silent imputation. No provider is selected
and no external request or credential is added by this step.

The next S2-03 slice adds immutable tenant-safe normalized-weather snapshots with
source reference and payload hash. It stores neither credentials nor raw payloads;
the selected adapter must retain raw evidence according to the documented policy.
The following S2-03 slice implements a provider-independent bounded retry and
primary-to-secondary failover policy. It accepts injected adapters only, records
attempt events for audit, honours a Retry-After delay only within the 30-second
default budget, and fails closed for authentication/configuration/schema faults.
It neither makes network calls nor serves stale weather. A selected, approved
provider adapter and its credentials, quota and TTL configuration remain required.
Source ZIPs retrieved through the cleaned Drive register and CRC-checked.
Nine canonical ML files normalized/created; three legacy paths retained as aliases.
Forecast worker, adapters, database additions and forecast endpoints are pending.

## Decisions and blockers

| ID | Decision / dependency | Owner | Consequence |
| --- | --- | --- | --- |
| S2-D01 | Hourly UTC origins; day-ahead 24–48h; AC power/energy target | ML/Backend; proposal | Distinguish from local calendar-day product |
| S2-D02 | Separate AC rating and existing DC capacityKw | Data/ML | Missing metadata blocks physical bound |
| S2-D03 | MODEL-001 physical/statistical candidate; no active model | ML | Physical library/parameters and calibration remain open |
| S2-D04 | Google selected for operational weather covariates; Solcast selected for production-contour GHI/DNI/DHI; OpenWeather Solar selected for historical issued-forecast training/backtest | Data Ops/Product | Configure credentials, quotas, TTL, rights and a live irradiance fallback; no provider adapter or production activation is enabled |
| S2-D05 | Real actuals and archived as-issued weather; meter boundary | Data/QA | Blocks meaningful historical accuracy evidence |
| S2-D06 | Numeric release limits, coverage/minimum samples and deadline | ML/QA/Product | Must be frozen before held-out evaluation |
| S2-D07 | Named owners, staging scheduler, storage and rollback evidence | Engineering/SRE | Blocks operational acceptance |

No blocker prevents documentation review or fixture-based implementation.
Live data, provider enablement and production acceptance remain gated as above.
Next engineering sequence and proposed review dates are in the [plan](README.md).
