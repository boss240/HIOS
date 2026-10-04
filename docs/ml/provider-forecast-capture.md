# Source-specific forecast evidence

`app/provider_forecast_capture.py` stores parsed forecasts independently of
the composed operational `weather_snapshot`. This lets Google retain weather
covariates without invented irradiance, and Solcast retain irradiance without
invented cloud cover. Open-Meteo instantaneous covariates retain their separate
sampling timestamp.

Each capture belongs to one tenant, plant, provider and mapping version. The
document contains only canonical numeric fields and UTC intervals. Receipt
time is mandatory; provider issue time is optional and remains null when the
provider does not supply it. Receipt must precede every target interval.
Duplicate, overlapping, reversed and already-started intervals are rejected.
Callers must explicitly select future intervals before submitting a batch.

Migration 0018 adds the capture table. Active membership and plant ownership
are checked before insertion; a checksum over the canonical document makes
the same capture idempotent. Database updates are forbidden to prevent later
rewriting of evidence. Raw payloads, request URLs, credentials and tokens are
excluded. This table is distinct from a production forecast run and does not
claim forecast accuracy or authorise equipment control.

`app/provider_forecast_collection.py` connects the Google/Solcast readers to
storage. It verifies membership and plant coordinates before making a request,
records receipt after parsing, and excludes already-started intervals explicitly.
The protected dashboard exposes GET/POST
`/dashboard/plants/{plant_id}/weather-captures`. POST requires `provider` to be
`google_weather` or `solcast` and `confirm` to be `CAPTURE_FORECAST`.
Server-side keys are required; absent keys return `WEATHER_KEY_NOT_CONFIGURED`
without synthetic replacement or a provider request. GET lists the latest 100
capture summaries for the authorised plant. No scheduler is enabled.
Accuracy evaluation must use receipt time as the availability
cutoff when provider issue time is unknown; it must never label that receipt as
a provider issue time. Comparisons require the same plant, target interval,
forecast horizon and approved actuals measurement boundary.

Validation includes pure late-capture/schema/alignment tests and a PostgreSQL
runtime test covering idempotence, cross-tenant denial and update rejection.
