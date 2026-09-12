# Weather-provider experiment catalogue

## Purpose

HIOS Forecast keeps the production contour narrow: **Solcast** supplies solar irradiance (GHI, DNI, DHI), while **Google Weather** supplies short-horizon weather covariates. The experiment layer stores an immutable forecast snapshot per provider, plant, issue time, target interval, and horizon. It does not replace the production contour until it has passed evaluation against measured generation.

The first comparison set is intentionally limited to three challenger channels:

| Provider | Proposed role | Why it is useful | Access decision |
|---|---|---|---|
| Open-Meteo Ensemble | Low-cost benchmark and scenario spread | Exposes individual ensemble members; useful to test uncertainty and weather-regime sensitivity around Kyiv oblast | Prototype only; confirm commercial data licence before customer delivery |
| meteoblue Learning MultiModel | ML multi-model challenger | Combines numerical models with observation, radar and satellite corrections | Register a server-side API key and agree commercial plan after benchmark |
| Meteomatics | Premium spatial challenger | Broad model/parameter catalogue and high-resolution downscaling option | Obtain business credentials after a benchmark specification is approved |

Google and Solcast stay enabled. The challengers are configured on the server, never from a browser form. No key or password is stored in a forecast payload or sent to the UI.

## Experiment contract

Each provider run must retain:

- provider identifier and model/version where supplied;
- plant identifier and coordinates;
- `issued_at`, forecast target interval, requested horizon and retrieval time in UTC;
- raw immutable provider payload in protected storage plus normalized weather fields;
- retrieval result, failure class and source-quality flags.

After actual inverter energy arrives, HIOS aligns energy to the same target interval. Evaluation is calculated separately for each plant, horizon and provider with MAE, RMSE, signed bias, nMAE, daylight MAPE and interval coverage. A challenger can receive a blending weight only after a fixed rolling sample and release-gate review; it cannot overwrite the incumbent automatically.

## Pilot plan: Погреби and Борщів

1. Collect Google, Solcast and up to three challenger snapshots every forecast cycle for the same 24-hour targets.
2. Ingest only read-only native inverter actuals and preserve the source interval semantics.
3. Start with 30 days of matched observations, then compare 1–6 h, 7–12 h and 13–24 h horizons separately.
4. Use correlation only as a diagnostic. Promote a blend only when held-out energy-error metrics improve for both the relevant weather regime and the individual plant.
5. Publish the customer view with forecast, confidence range, provider evidence and the labelled model release—not a hidden vendor score.

## Current boundary

The commercial dashboard is an interface prototype. It has no browser credential entry, no automatic provider calls, no scheduler, no automatic model promotion and no claimed live accuracy. Deye actuals/native identifiers and final tilt, azimuth and AC capacity remain required before operational accuracy can be measured.

## Sources

- [Open-Meteo Ensemble API](https://open-meteo.com/en/docs/ensemble-api)
- [meteoblue Weather APIs overview](https://docs.meteoblue.com/en/weather-apis/introduction/overview)
- [Meteomatics Weather API](https://www.meteomatics.com/en/weather-api/)
