# Deye pilot execution runbook

Related issue: #10 (EPIC-005); sprint tracking: #22. This procedure starts
only after Deye has supplied the AppSecret for the already registered,
read-only application. It is a manual non-production procedure: it does not
enable a scheduler, CI job, ingestion service or control operation.

## Preconditions

- The Deye application is approved for station and device monitoring only.
- The AppSecret has been received through Deye's approved support or developer
  channel.
- The user has confirmed that the two selected plants remain in scope.
- A designated operator has an approved secret manager or GitHub repository
  secrets access.
- The owner-consent record and a per-plant mapping version exist before any
  historical data is retained.

## Secret names

Store values only in the approved secret manager. If GitHub repository secrets
are used for the controlled operator environment, use these exact names:

| Secret name | Purpose |
| --- | --- |
| `DEYE_APP_ID` | Deye application identifier. |
| `DEYE_APP_SECRET` | Deye application secret. |
| `DEYE_ACCOUNT_EMAIL` | Approved Deye account used for the read-only token flow. |
| `DEYE_ACCOUNT_PASSWORD` | Password for that approved account. |
| `DEYE_COMPANY_ID` | Optional Deye business-account context; omit when not applicable. |

Never place a value in a workflow file, command history, issue, pull request,
test fixture, log, output artifact or source-control commit. GitHub Actions may
be used only by the explicitly manual, bounded read-only workflows in this
repository. They must not upload raw frames or artifacts, persist provider rows,
or enable scheduling.

## Controlled discovery

Run the discovery command only from a secured operator environment after
loading the secret values as environment variables:

```text
python scripts/deye_pilot_discovery.py --execute
```

The command calls the fixed Deye read-only client, selects only the two
approved pilot names and writes only the canonical pilot key and native station
ID to standard output. It makes no request when `--execute` is omitted.

Expected result shape:

```json
{
  "selected_pilots": [
    {"pilot_key": "deye-pilot-borshchiv", "station_id": 0},
    {"pilot_key": "deye-pilot-pohreby", "station_id": 0}
  ]
}
```

The zeroes above are placeholders, not plant identifiers. Do not paste the
actual station IDs into a public issue or pull request.

## Evidence to retain

For each pilot, place the following redacted record in the approved restricted
operations store:

| Field | Required value |
| --- | --- |
| Event type | `deye.pilot_station_discovery` |
| Occurred at | UTC timestamp of the completed request |
| Actor | Authorized operator reference |
| Pilot key | `deye-pilot-pohreby` or `deye-pilot-borshchiv` |
| Native station ID | Retrieved value; restricted access |
| Request class | `POST /v1.0/station/list` |
| Code version | Immutable Git commit SHA used for the command |
| Result | `success`, `rejected`, or `incomplete` |
| Mapping version | Pending until field mapping is reviewed |

Do not retain the AppSecret, account password, bearer token, raw response,
full plant display name, address, serial number or device identifier in this
record.

## Stop conditions and next gate

Stop immediately and record `rejected` or `incomplete` when authentication
fails, either pilot is absent, Deye returns an unexpected schema, an ID cannot
be restricted to the approved plant scope, or the operator cannot write the
redacted evidence.

After both IDs are verified, update the restricted pilot register and prepare
the field-mapping review. The next approved request, if authorized, is a
bounded device discovery followed by one closed UTC day of history for each
plant. No telemetry may enter training, evaluation or production services
until the per-plant quality, reconciliation and tenant-isolation gates pass.

## Controlled hourly collection

After the two pilots are discovered, an operator may run the manual workflow
`Deye pilot hourly read-only collection` for **one completed UTC date**. It
uses the fixed station-list and station-history read paths to select only
`Погреби` and `Борщів`, then returns per-hour frame coverage and quality
statistics for each pilot.

The workflow requires both the ISO date and the exact acknowledgement
`READ_ONLY_HOURLY`. It has read-only repository permissions, no schedule and a
five-minute execution limit. It does not upload an artifact, log a raw Deye
frame, save a token, modify an inverter or create a database row.

The result is collection evidence, not yet a calibrated actual-generation
series. Before hourly values can be normalized and retained for forecast
training or evaluation, the Deye field names, timezone, units, interval
meaning, consent record and per-plant mapping version must be approved. Until
then, the report explicitly states `not_written_pending_field_mapping`.
