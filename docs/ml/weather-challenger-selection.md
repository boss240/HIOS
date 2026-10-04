# Additional weather sources for the two pilot plants

Reviewed: 2026-10-05. This is an integration decision, not a claim of measured
accuracy or enabled provider access. Google Weather and Solcast remain the
selected operational roles. Other catalogue entries are candidates.

## Integration order

| Candidate | Useful input | Evidence and unresolved conditions | Next implementation gate |
|---|---|---|---|
| Open-Meteo, fixed model runs | Hourly solar radiation and weather; archived individual runs | Single Runs API exposes run-specific archives; general historical weather and historical forecast series must not silently substitute for a selected run. Commercial access and retention conditions must be confirmed. | Select a commercial plan, model and run metadata; implement run-specific ingestion and immutable source lineage. |
| Meteomatics | Direct, diffuse and global radiation; interval means and weather | API distinguishes instantaneous flux from interval statistics. A one-hour sampling step does not make instantaneous flux an hourly mean. | Obtain approved account/contract; select explicit hourly mean fields, units, model and initialization metadata. |
| meteoblue | Multi-model forecast and solar variables | Forecast API offers limited prior forecast history; long-term storage requires an appropriate caching license. History products are not automatically as-issued forecast runs. | Confirm forecast/solar package, permitted archival duration and issue/run timestamps before collecting. |
| EOSDA Weather, Ukrainian partner priority | Cloud, temperature and other weather covariates | Basic documentation describes 3-hour updates; high-accuracy examples show hourly intervals. It says High Resolution Weather sales ended in early 2025. Listed response fields do not establish GHI/DNI/DHI availability. | Request current product availability, Ukrainian coverage, hourly semantics, storage rights and radiation fields. Use as a covariate challenger until irradiance is documented. |
| Contractual local Ukrainian service | Independent local forecast or measurements | No provider API contract or licensed sample has yet been supplied. A website forecast is not an approved scraping interface. | Obtain API/feed contract and sample with timestamps, units and retrieval rights; then build a specific adapter. |

Sources:

- [Open-Meteo Single Runs API](https://open-meteo.com/en/docs/single-runs-api)
  and [pricing and access](https://open-meteo.com/en/pricing).
- [Meteomatics radiation parameters](https://www.meteomatics.com/en/api/available-parameters/weather-parameter/radiation/)
  and [initialization metadata](https://www.meteomatics.com/en/api/request/meta-requests/).
- [meteoblue Forecast API](https://docs.meteoblue.com/en/weather-apis/forecast-api/overview)
  and [archival caching requirements](https://docs.meteoblue.com/en/services/weather-stations/virtual-weather-stations).
- [EOSDA basic weather providers](https://doc.eos.com/docs/weather/basic-weather-providers/)
  and [field weather products](https://doc.eos.com/docs/field-management-api/weather/).

## Comparable evidence and mixing

For each plant, archive each forecast before its target interval. Preserve the
provider, model, run/issue timestamp if supplied, receipt timestamp, UTC interval,
units, aggregation semantics, mapping version and immutable document checksum.
Unknown issue times stay unknown. Freeze training and evaluation inputs at their
forecast origin; later weather updates may not replace earlier forecasts.

Use one physical PV transformation and confirmed installed plant parameters
across irradiance challengers. Compare forecasts with facts of a compatible
measurement boundary. Device PV kWh must not be scored as plant AC output, and
cloud percentages or radiation W/m² must not be scored directly against kWh.

Evaluate rolling held-out days separately for each plant and lead-time range.
Report hourly error, daily energy bias, coverage and sample count. Correlation
alone is insufficient: two sources may be highly correlated and share the same
bias. Estimate blend weights only on training days and assess improvement on
later held-out days against the unchanged baseline. Retain the baseline when
coverage or comparative evidence is insufficient; do not invent a target
accuracy percentage or licence-sale eligibility from zero paired hours.

## Current evidence gaps

The operational archives contain Google/Solcast captures, but the actual device
PV archive currently contains only one day per pilot. The deployed analysis has
no eligible forecast/fact pairs yet. Installed DC/AC capacity, orientation and
meter boundary remain unconfirmed. Additional provider credentials, contractual
rights and tested ingestion adapters are not enabled by this document.
