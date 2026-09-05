# Repository review and merge policy

Effective 2026-09-05, related #5/#19.

main requires an up-to-date PR branch, successful Documentation baseline,
Sprint 1 baseline files and (once introduced) Runtime integration checks,
resolution of conversations and one approval. New commits dismiss stale approvals.
Force pushes and branch deletion are disabled.

The repository currently has one collaborator, owner boss240. GitHub disallows
self-approval. Administrator enforcement is therefore disabled: the owner can
perform an explicitly authorized administrative merge after reviewing the diff
and verifying all required checks. This is an owner exception, not independent
peer approval. No approval is fabricated. Record the reviewed commit and checks
in the PR/issue evidence. Add another reviewer and enable administrator enforcement
when independent review becomes available.

PR #20 was reviewed against its requested documentation/contract scope, its
OpenAPI/example checks and successful CI, and merged under the owner's explicit
instruction to review/merge. Runtime changes follow the same evidence-based
owner exception while only one collaborator exists.
