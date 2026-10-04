# Deye instantaneous power to hourly energy

`app/deye_power_integration.py` prepares derived hourly estimates for the two
pilot plants. It does not call Deye or write actuals to PostgreSQL.

The caller supplies a verified `W` or `kW` unit. No unit is guessed from field
names, installed capacity, sample magnitudes or the existing test fixtures.
The official schema inspected on 2026-10-04 describes `generationPower` as a
number without a unit:
https://developer.deyecloud.com/openmcp/docs/deye-open-mcp-tools.html
That schema alone is insufficient to approve production measurement mapping.

The algorithm integrates piecewise linear instantaneous power, splitting
segments at UTC hour/day boundaries. It accepts at most 10-minute gaps by
default; the caller may explicitly set a limit from 1 to 900 seconds.
Invalid power breaks both adjacent segments. Duplicate/unordered/invalid
timestamps reject the batch. There is no extrapolation or gap filling.

Each of the 24 UTC hours reports covered seconds, derived kWh and whether all
3600 seconds are covered. No coverage yields null energy. Partial coverage
yields only the covered energy and must not be scored as full-hour actuals.
These estimates are not measured meter energy. They must retain their method,
source unit, approved mapping version and coverage when eventually persisted.

Remaining integration gates: confirm provider units and instantaneous field
semantics, obtain boundary samples without unbounded history requests, connect
the approved tenant/plant binding, persist provenance and reject incomplete
hours in the accuracy evaluation. Existing hourly CSV import remains available.
