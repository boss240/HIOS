# Per-plant provider ensemble

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
