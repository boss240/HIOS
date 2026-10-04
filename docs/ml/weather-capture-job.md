# Bounded source forecast collection job

The Azure Container Apps job runs `app.weather_capture_job` against the same
private database as the dashboard. It has an explicit tenant, operator subject
and JSON allowlist of one or two plant IDs. It never discovers or adds plants,
calls Deye, changes inverter settings or publishes a calibrated forecast.

Initial schedule: 06:00 and 18:00 UTC, two runs per day. This is a conservative
pilot cadence, not a claim about provider subscription quotas. Verify the
applicable provider contract before increasing it. Azure evaluates scheduled
jobs in [UTC](https://learn.microsoft.com/en-us/azure/container-apps/jobs).

The job attempts Google and Solcast once per authorised plant. A PostgreSQL
session advisory lock serialises overlapping job executions for that source.
A successful capture in the current UTC half-day satisfies the slot, including
captures made manually. Closing the database connection releases the lock.
Failures do not retry inside the job or erase successful sibling captures.
Azure replica retry limit is zero, parallelism one and timeout 180 seconds.

Only `DATABASE_URL`, `GOOGLE_WEATHER_API_KEY` and `SOLCAST_API_KEY` are copied
into job secrets. ACR pull uses the existing managed identity. The explicit
scope is provided as `HIOS_CAPTURE_TENANT`, `HIOS_CAPTURE_SUBJECT` and
`HIOS_CAPTURE_PLANTS`; none of it is printed in logs. Logs contain provider,
ordinal plant index, outcome, interval count or error class only.

The initial production scope is the coordinate-verified Pohreby record.
Borshchiv remains excluded until its Deye ID is unambiguously matched to its
passport. Existing duplicate records are not deleted by this job.

Deployment must verify the image digest, job schedule, secret references,
successful manual execution and persisted capture summaries. A successful
execution that skips an existing slot proves the skip path; it does not prove
a new scheduled capture. Inspect later scheduled executions and archives
before reporting unattended collection as observed.
