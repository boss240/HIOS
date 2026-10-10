# Daily read-only Deye collection

`python -m app.deye_daily_capture` collects missing days in the last seven completed UTC days for
the two approved pilots. Required environment variables are `DATABASE_URL`,
`HIOS_CAPTURE_SUBJECT`, `HIOS_CAPTURE_TENANT`, `HIOS_CAPTURE_PLANTS` (ordered
JSON array: Pohreby, Borshchiv), and the server-side `DEYE_APP_ID`,
`DEYE_APP_SECRET`, `DEYE_ACCOUNT_EMAIL`, `DEYE_ACCOUNT_PASSWORD`.

`HIOS_DEYE_LOOKBACK_DAYS` defaults to 7 and accepts 1–31. Stored days are
skipped before history requests; missing days are processed oldest first and
the first failure stops the run. This catches intermittent access failures
within the window without retrying a rejected request during the same run.
Older gaps require an explicitly bounded backfill. The current UTC day is
never collected. Until this change is deployed, Azure still collects one day.

The collector checks owned plant coordinates, an unambiguous station/device
match, and the device checksum against existing captures before collection.
It requires an existing verified read-only binding; it does not create consent
or promote pending bindings. Canonical collection rechecks membership and device
ownership, locks the device scope, and skips already stored days. A failed day
stops the run. There are no automatic retries or equipment control calls.

## Azure deployment evidence, 7 October 2026

- Job: `hios-deye-daily-capture`, resource group `rg-hios-forecast-weu`.
- Schedule: `0 7 * * *` UTC; one replica, retry limit 0, timeout 900 seconds.
- CPU 0.25, memory 0.5 GiB; existing user-assigned identity and secret references.
- Initial control execution: `hios-deye-daily-capture-6v9fo6w`, Succeeded.
- Current job contains the equivalent inline collector on image
  `hiosforecastca26.azurecr.io/hios-forecast:release-143-144`. This module is for
  the next image release; do not switch to the module command on the old image.

Check the exact execution status and sanitized outcomes before retrying. Never
restart merely because observation timed out. Future scheduled execution and
fresh-day persistence remain to be verified after the next scheduled run.

The separate bounded backfill for 23 September–6 October succeeded. Protected
PostgreSQL readback showed 14 daily captures per pilot: 289 complete UTC hours
for Pohreby and 273 for Borshchiv out of 336 hours each.

These measurements are device `TotalSolarPower` in W, integrated to device kWh.
They are not confirmed whole-plant AC actuals. Google/Solcast alignment for
5 October yielded 16 and 17 complete paired hours respectively. No generation
accuracy or commercial licence eligibility has been established.

Solcast currently returns HTTP 402; Google captures continue to be persisted.
The older Solcast archive is not evidence of current tariff access. Physical
plant parameters and measurement boundaries still require confirmation.
