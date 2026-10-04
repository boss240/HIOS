# Protected device solar archive

`GET /dashboard/plants/{plant_id}/solar-history?start=YYYY-MM-DD&end=YYYY-MM-DD`
requires dashboard authentication and active membership in the owning tenant.
Both inclusive UTC dates are required; the window cannot exceed 31 days.
Missing ownership is denied. Invalid windows return 400.

Each returned capture includes its UUID, canonical document checksum, receipt
time, day, mapping version, sample count and 24 derived hourly records with
covered seconds and complete/partial flags. Only the latest receipt for each
device/day is selected. The response excludes serial numbers and device hashes.
The maximum response is 124 device/day records; larger selections are rejected.

The `device_only` scope is mandatory. These are PV power samples and integrated
device energy estimates, not certified whole-plant AC meter readings. Missing
coverage is retained. The endpoint never calls Deye, imports data or controls
equipment.

The same protected window is available as an Excel download at
`/dashboard/plants/{plant_id}/solar-history.xlsx?start=YYYY-MM-DD&end=YYYY-MM-DD`.
The dashboard displays its download link after a successful archive read.
It preserves numeric energy, blank missing values, coverage seconds, statuses,
UTC dates, capture UUID/checksum/receipt and mapping version. Strings are exported
as text, never formulas. Download responses disable caching. The file represents
device PV energy estimates and must not be relabeled as plant AC meter readings.

## Verified cloud archive and acquisition limitation

On 2026-10-04 the PostgreSQL read-back audit confirmed one capture per pilot for
2026-10-03: Pohreby 290 samples and Borshchiv 291 samples, each with 20 complete
hours. A bounded 14-day acquisition failed. A subsequent cloud authentication
audit returned Deye code 2101025 (HTTP 200); no additional days were present.
The code's cause is not established. Existing captures remain usable; do not
claim 14-day coverage, successful continuous acquisition or evaluated forecast
accuracy. Historical forecast evidence must precede its target intervals.
