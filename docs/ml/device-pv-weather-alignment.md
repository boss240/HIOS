# Exact hourly weather and device PV alignment

`align_device_pv_weather` pairs validated selected Google/Solcast capture inputs
with one immutable device PV capture. The caller must establish shared active
tenant/plant ownership before invoking this pure function. This function has no
database/provider access, writes, calibration or equipment control.

The actual document checksum is verified and all 24 hourly energy estimates
are reproduced from stored power samples. Future/unclosed weather targets,
missing actual hours and partial coverage are counted as exclusions. Only exact
closed UTC hours with 3600 covered seconds are paired. Real zero energy remains
zero; missing energy cannot become zero. Actual receipt and forecast origin must
precede analysis time. The selected capture IDs, hashes, receipt and optional
provider issue timestamps are retained; unknown issue time is not invented.

The output deliberately separates weather irradiance in W/m2 from derived device
PV energy in kWh. It is an analysis dataset, not an AC generation forecast error
score or a license qualification. PV/AC measurement scope must be established
before generation accuracy is evaluated. Weather-to-PV correlation, when added,
cannot alone prove energy forecast accuracy or out-of-sample improvement.

Current real archives do not yet provide a historical overlap: device PV data is
stored for 2026-10-03, while the retained weather forecasts were collected later.
Do not use a later forecast or reanalysis as an earlier as-issued forecast.
Provider weights and accuracy remain unevaluated until eligible pairs exist.
