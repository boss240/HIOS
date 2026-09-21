# Programme: forecast ensemble, integrations and commercial rollout

Status: proposal for approval before production implementation.  It converts the
existing HIOS provider catalogue and read-only inverter-cloud contract into a
measurable rollout; it does not authorize remote control of any device.

## 1. Product outcome

HIOS produces an hourly forecast for each tenant-owned solar plant and preserves
the evidence needed to answer four questions:

1. Which forecast was known before a target hour?
2. Which weather source and model produced it?
3. What did the plant actually generate in that hour?
4. Did an alternative source or model improve the error enough to become the
   default for that plant and horizon?

The first portfolio is **Погреби** and **Борщів**.  Each later plant follows the
same tenant-scoped onboarding route.  All inverter access remains read-only.

## 2. Weather-source operating model

| Role | Providers | Purpose | Entry condition |
| --- | --- | --- | --- |
| Production contour | Google Weather + Solcast | Hourly weather context plus solar irradiance | Credentials, quota guardrails and stored as-of responses |
| Challenger | Open-Meteo Ensemble | Independent model scenarios and no-key benchmark | Version, model identifiers and response provenance retained |
| Challenger | Meteomatics, meteoblue | Commercial multi-model comparison | Contract, cost owner and caching terms confirmed |
| Ukrainian/geospatial research | EOSDA Weather; approved local partner | Local coverage or value-added geospatial features | Written data contract and field/timezone mapping |
| Fallback | Remaining configured source | Degraded forecast only; never silently replaces the production contour | Explicit failover policy and quality flag |

A source becomes **configured** only after its credentials are stored outside
source code, rate limits are recorded, and one plant’s historical backtest passes.
A source becomes **production** only after the champion-selection gate below.
No raw source response may overwrite a prior forecast: each retrieval carries
provider, model/run identifier when supplied, retrieval time, valid interval,
units, coordinates, and a payload digest.

## 3. How the ensemble learns

1. At every forecast origin, retrieve and store each source separately before
   the target interval starts.  Normalize units and timestamps to UTC.
2. Produce independent candidates: physical baseline, Google+Solcast baseline,
   and one candidate for each challenger or approved blend.
3. After actual generation arrives, exclude intervals flagged as outage,
   curtailment, missing measurement, or invalid plant metadata.  Keep the
   exclusion reason in the evidence table.
4. Score only comparable daylight intervals by plant and horizon: MAE (kW),
   normalized MAE, WAPE (energy), signed bias, coverage/completeness, and sample
   count.  Do not compare a forecast made after the fact with one made before it.
5. Recalculate a rolling scorecard weekly from an immutable 30-day minimum
   evidence window.  A candidate may become champion only if it improves the
   agreed primary metric against the current champion, has sufficient valid
   samples, has no material degradation in bias or coverage, and can be
   reproduced from stored provenance.
6. Keep the existing champion when evidence is insufficient or results are tied.
   Any promotion records the decision date, metric window, model/provider
   versions, approver and rollback candidate.

The required improvement percentage is **not a universal fixed number**. It is a
versioned per-product acceptance parameter, agreed before each customer trial so
marketing never claims an unverified accuracy percentage. The customer sees the
actual achieved metrics and sample count.

## 4. Fast, safe plant onboarding

### Customer flow

1. Select inverter cloud and enter a station/site ID or approve an owner-consent
   connection.
2. HIOS discovers only the plant and device metadata permitted by that cloud.
3. The operator completes only information a cloud usually cannot know reliably:
   AC/DC capacity, coordinates/time zone, tilt, azimuth, meter boundary,
   mounting, commissioning date and notes.
4. HIOS validates the profile, displays the data source for each field, and
   blocks forecast publication if essential values are missing.
5. A read-only binding and field mapping are reviewed. Historical actuals begin
   only after the access status is confirmed.
6. The plant enters **Cold start**; after enough valid actuals, it enters
   **Calibrating**, then **Eligible for champion selection**.

Never ask a customer to place an inverter password in an HIOS form. Use a
provider consent flow, a secret reference owned by the platform, or a CSV/XLSX
export with a visible source reference.  Device-control scopes are out of scope.

### Minimum acceptance contract for every connector

- owner consent, tenant and plant ownership are recorded;
- read-only scope is technically enforced;
- native station/device IDs and canonical fields are mapped with a version;
- UTC timestamps, interval semantics, kW/kWh units and completeness are tested;
- retry/backoff, cache and rate limits are documented;
- a connector can be disabled per tenant without deleting historical evidence.

## 5. Inverter-cloud first wave in Ukraine

The list is an integration priority, not a claim that all APIs are publicly
available or ready. Each vendor requires its own contract and technical proof.

| Priority | Cloud/platform | HIOS status | First work item |
| --- | --- | --- | --- |
| 1 | Deye Cloud | Pilot in progress | Finish read-only discovery and hourly actuals mapping |
| 2 | Huawei FusionSolar | Qualification | Obtain approved Open API/partner route and sample payload |
| 3 | GoodWe SEMS | Qualification | Confirm commercial API and owner consent model |
| 4 | Sungrow iSolarCloud | Qualification | Confirm developer access and historical-export path |
| 5 | Solis Cloud | Qualification | Confirm API programme and sampling limits |
| 6 | Growatt ShineServer | Qualification | Confirm partner/read-only access and history availability |
| 7 | SolarEdge ONE | Qualification | Register OAuth application and validate API V2 scope |
| 8 | SMA Sunny Portal | Qualification | Confirm OAuth/partner route for the Ukrainian fleet |
| 9 | Fronius Solar.web | Qualification | Confirm tenant ownership and API-key route |
| 10 | Victron VRM | Qualification | Validate token route and meter-boundary mapping |

For every vendor, the first deliverable is a non-secret **connector evidence
card**: official documentation URL, access type, intended scopes, data-centre,
field map, history availability, rate limits, customer consent text, sample
response schema and negative-test result. A code adapter is not started until
that card is accepted.

## 6. Trial and licence pathway

### Pilot/test benefit

Offer an invite-only, time-limited trial to a customer with compatible hardware.
The trial includes selected plants, hourly forecast dashboard, CSV/XLSX export,
actual-versus-forecast scorecard and a transparent data-quality status. Its end
condition is a written pilot report, not a promise of a specific revenue result.

### Conversion evidence

A conversion offer is prepared when the pilot has: (a) customer-authorized data,
(b) a documented eligible evidence window, (c) published measured accuracy by
horizon, (d) an agreed value use-case such as RDN planning, storage/load schedule
or O&M, and (e) no unresolved data-quality warning that could invalidate the
metric. The report states the achieved percentage and denominator rather than
using a generic advertising figure.

### Licence layers to approve commercially

| Layer | Entitlement boundary | Commercial decision still required |
| --- | --- | --- |
| Trial | limited plants, data-retention window, dashboard and export | duration, limits, support level |
| Forecast licence | plant count, forecast horizons, ensemble/benchmark access | price, term, SLA, included users |
| Portfolio licence | multi-plant and tenant reporting/API | price tiers, API quota, roles |
| Enterprise/O&M | custom integration, evidence exports, support | contract, data processing, support scope |

Billing activates only an entitlement after a signed commercial policy and a
payment provider are chosen. The current HIOS subscription model remains a
state/entitlement design; it does not contain prices or payment processing.

## 7. Delivery sequence

1. **Evidence first:** import 14–30 days of validated actuals for the two pilots;
   complete source-data and quality scorecards.
2. **Ensemble runtime:** store as-of forecasts for Google, Solcast and
   Open-Meteo; implement one reproducible challenger scorecard.
3. **Onboarding v2:** field provenance, readiness checklist and a connector
   evidence-card workflow.
4. **Vendor wave:** Deye, then Huawei and GoodWe only after approved access;
   apply the same connector gate to the remaining seven platforms.
5. **Commercial pilot:** approve trial terms and a metric definition, recruit a
   small compatible cohort, then use verified reports to define licence packages.

## 8. Decisions required before implementation

- Approve the first challenger order: Open-Meteo, then EOSDA, then one paid
  multi-model provider (Meteomatics or meteoblue).
- Approve whether the trial begins after 14 or 30 valid days of actuals.
- Approve the primary customer metric (normally normalized MAE for hourly
  generation) and the minimum evidence window.
- Confirm the first three inverter clouds after Deye: Huawei, GoodWe and Sungrow
  are proposed; their API access must still be confirmed by each vendor.
- Approve commercial terms, price and data-processing documents separately.

## Official references

- [Google Weather API overview](https://developers.google.com/maps/documentation/weather)
- [Solcast radiation and weather forecast endpoint](https://docs.solcast.com.au/docs/section/irradiance-weather-data#getDataForecastRadiationAndWeather)
- [Open-Meteo API documentation](https://open-meteo.com/en/docs)
- [DeyeCloud developer portal](https://developer.deyecloud.com/)
- [SolarEdge developer API](https://developer.solaredge.com/)
- [Huawei FusionSolar ecosystem overview](https://solar.huawei.com/es/products/smart-pv-plant-management-system/)
