# ML Operations Checklist

Related issue: #10  
Source: HEDS-010 ML / AI Operations Manual

## Development checklist

- [ ] Model purpose is documented.
- [ ] Input data sources are documented.
- [ ] Feature pipeline version is traceable.
- [ ] Model/version identifier is assigned.
- [ ] Evaluation dataset or method is documented.
- [ ] Forecast quality metrics are recorded.
- [ ] Known limitations are listed.

## Release checklist

- [ ] Model registry entry exists.
- [ ] Forecast output schema is documented.
- [ ] Data quality checks are satisfied or exceptions are documented.
- [ ] Weather provider assumptions are reviewed.
- [ ] Degraded-mode behavior is documented.
- [ ] QA evidence is linked from the release or issue.

## Operations checklist

- [ ] Forecast job schedule is defined.
- [ ] Job failures are observable.
- [ ] Provider failures are logged with provider metadata.
- [ ] Forecast freshness is measurable.
- [ ] Model/version changes are auditable.
- [ ] Rollback path is documented before production model changes.

## Open decisions

- Model monitoring metrics.
- Drift detection approach.
- Retraining cadence.
- Manual override or rollback workflow.
