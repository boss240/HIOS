# Device solar history: bounded read-only acquisition

The reader `device_solar_history_for_day` requests one selected device and one
completed UTC calendar day through `/v1.0/device/historyRaw`. It requests only
`TotalSolarPower` and `PVDailyPowerGenerationActive`, with inclusive epoch-second
bounds. Callers must obtain the serial from the approved station device list.
Serials, tokens and station identifiers must not enter public reports.

Official schema: https://developer.deyecloud.com/openmcp/docs/deye-open-mcp-tools.html
(`device_history_raw`). The public EU Swagger endpoint also lists this path.

## Live evidence, 2026-10-04

For the closed UTC day 2026-10-03, one device under each approved pilot returned
history: Borshchiv 291 rows and Pohreby 290 rows. Both returned `time` and
`itemList`, including `TotalSolarPower` with unit W and
`PVDailyPowerGenerationActive` with unit kWh. Other listed devices rejected the
request with code 2104005; one request failed without a provider code. Their
absence must not be treated as zero generation or complete plant coverage.

This proves that unit-bearing device solar history is available, not that all
plant devices, every hour, timestamps or energy totals have been validated.
No measurements were persisted by this probe. The day-counter field must not
be summed across samples. Device timestamps, gaps, counters and device coverage
still need validation before writing plant hourly actuals. These units do not
establish units or semantics for station `generationPower`.

The reader has no retries, scheduling, equipment control or database writes.
Local transport tests cover exact day bounds, selected measurement keys, one
request only and rejection of invalid serials or unfinished/ambiguous dates.
