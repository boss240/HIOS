# Defect Lifecycle

Related issue: #16

## States

| State | Meaning |
| --- | --- |
| New | Defect reported, not yet triaged. |
| Triaged | Impact and priority confirmed. |
| In Progress | Fix is being implemented. |
| Review | Fix is ready for review. |
| QA | Fix is ready for validation. |
| Done | Fix accepted and closed. |
| Rejected | Not a defect or not planned. |

## Required defect fields

- Summary
- Environment
- Steps to reproduce
- Expected result
- Actual result
- Impact
- Evidence or screenshot when available
- Related issue or release gate

## Severity guide

- Critical: release-blocking or data/security-impacting.
- High: major workflow blocked.
- Medium: workaround exists.
- Low: minor polish or documentation issue.
