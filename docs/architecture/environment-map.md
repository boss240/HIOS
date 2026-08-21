# Environment Map

Related issue: #6  
Source: HEDS-003 System Architecture Document and HEDS-007 DevOps and Deployment Architecture

## Purpose

This document defines the first deployment-environment baseline for Sprint 1 planning.

## Environments

| Environment | Purpose | Data policy | Access |
| --- | --- | --- | --- |
| Local | Developer setup and documentation validation | Synthetic or fixture data only | Individual contributor |
| Development | Shared integration workspace | Synthetic or anonymized test data | Engineering team |
| Staging | Release candidate validation | Production-like non-sensitive data | Engineering, QA, selected stakeholders |
| Production | Live customer operation | Production data | Restricted operations access |

## Environment expectations

- Configuration must be environment-specific and not hard-coded.
- Secrets must not be committed to the repository.
- Production access should be audited.
- Staging should support acceptance evidence before release.
- Local setup should remain lightweight until implementation stack is selected.

## Required future work

- Select hosting/runtime platform.
- Define secret-management mechanism.
- Define database provisioning and migration workflow.
- Define observability requirements per environment.
- Define backup, restore, and disaster-recovery expectations.
