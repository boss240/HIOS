# Per-plant provider ensemble

`app.as_issued_ensemble` requires a real `captured_at_utc` and common
`forecast_origin_utc` for each comparison. A provider issue time may be null;
it never replaces receipt evidence. A forecast received after the comparison
origin, different origins across providers, or differing actual values for
the same plant/hour excludes the entire hour for all providers. This prevents
unequal forecast horizons, retrospective retrieval or conflicting actuals
from changing correlation and weights. Numeric values and daylight/quality
metadata are validated even when a row would later be excluded.

This is an evaluation boundary, not a measured accuracy result. Database
captures, modelled provider power and approved actuals still need to be joined
with their original provenance before an operational mix can be enabled.

The operational baseline remains Google Weather plus Solcast. Challenger sources are retained as independent, as-issued forecast runs and are not substituted into the operational path merely because a response is available.

`app.provider_ensemble` derives one profile per HIOS plant key from paired provider forecasts and measured AC power. Each profile records pair count, MAE, signed bias and Pearson correlation. The hourly mix uses normalized inverse-MAE weights with an explicit 1% rated-AC error floor, avoiding an infinite weight for a short perfect sample.

The mixer rejects cross-plant calibration and incomplete hourly coverage. Therefore «Погреби» and «Борщів» always receive separate weights, and a challenger outage cannot silently change the composition of an hourly result.

The current candidates are:

| Role | Candidate | Use |
| --- | --- | --- |
| Baseline covariates | Google Weather | temperature, cloud and wind |
| Baseline irradiance | Solcast | GHI, DNI and DHI |
| Challenger benchmark | Open-Meteo | independent multi-model comparison and archived runs |
| Challenger commercial | Meteum | independent API forecast and history evaluation |
| Local source | Ukrainian Hydrometeorological Center | only under an approved data-access agreement |

No source is activated by this module. API keys, provider calls, retention, scheduling and champion promotion require separate operational approval.
