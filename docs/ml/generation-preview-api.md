# Protected candidate generation preview

`POST /dashboard/plants/{plant_id}/generation-preview` uses the dashboard's
configured authentication plus active tenant membership and plant ownership.
It reads two explicitly selected immutable captures and the owned plant's
passport. It makes no provider calls, writes no forecasts and issues no
equipment commands. This internal dashboard route is not the public licensed
forecast API.

Request fields (all required, no extras):

```json
{
  "captureIds": ["<Google capture UUID>", "<Solcast capture UUID>"],
  "forecastOriginUtc": "2026-10-04T19:45:00Z",
  "performanceRatio": 0.85,
  "temperatureCoefficientPerC": -0.004
}
```

The coefficient values above illustrate the request format; they are not
approved values for the pilots. The forecast origin must be aware and not in
the future. Source receipt must precede or equal that origin, and target hours
must follow it. The route does not silently select latest captures for replay.

Passport requires latitude, longitude, DC/AC capacity, tilt, azimuth and an
explicit meter boundary. Missing fields return HTTP 409 with
`PLANT_PREVIEW_NOT_READY` and `missingFields`. Invalid configuration/timing
returns 400; foreign plant/capture or inactive membership returns 403.

Success returns `mode=uncalibrated_candidate`, `persistence=not_written`,
`accuracy=not_evaluated`, explicit trial configuration and hourly candidate
power/energy with quality flags and both immutable capture sources. The result
is not a registered/approved production run. UI controls, runtime deployment,
configuration approval and generation calibration remain separate work.
