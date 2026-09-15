# Plant onboarding and inverter-cloud connector boundary

HIOS supports a growing catalogue of solar plants. The operator enters only
passport and engineering data that an inverter cloud normally cannot establish
reliably: coordinates, AC capacity, array geometry, meter boundary,
commissioning date and notes. A value may remain unknown until verified; it is
never invented from a provider label.

## Read-only cloud discovery

A provider binding contains a native plant ID, a secret-manager **reference**,
an owner-consent reference and a mapping version. It does not contain a
password, API key, token, serial-number payload or a control permission.
Bindings are read-only and move through `pending`, `verified` or `blocked`.

The first catalogue contains Deye Cloud, Fronius Solar.web, GoodWe SEMS,
Growatt ShineServer, Huawei FusionSolar, SMA Sunny Portal, SolarEdge One,
Solis Cloud, Sungrow iSolarCloud and Victron VRM. These are connector
contracts, not a claim that every vendor grants every field. Field availability
is verified per owner, API contract and plant.

For each approved binding the future adapter can retrieve only the documented
read-only fields: native plant/device identifiers, timestamps, AC power,
energy with its semantics, operating state, alarms, battery/grid values and
historical intervals where the provider permits them. HIOS preserves source
reference, retrieval time and mapping version before data can enter model
training or evaluation.

No background synchronisation is enabled by this change. A provider call needs
separate approval, owner consent, a secure secret reference and a reviewed
field mapping.