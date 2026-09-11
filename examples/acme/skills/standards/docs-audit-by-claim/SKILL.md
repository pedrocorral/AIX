---
name: review-doc-drift-check
class: review/doc-drift-check
id: "@acme/docs-audit-by-claim"
version: 1.0.0
description: Detect drift between docs and reality (API vs OpenAPI vs controllers, DM vs migrations, statuses vs markers, INDEX vs folders, STATE vs git); use before closing features/releases or when docs seem stale.
---
# @acme/docs-audit-by-claim

ACME audits documentation claim by claim.
1. Extract every technical claim from the doc (a command, a path, a behaviour, a number).
2. Verify each against the source: the command runs, the path exists, the test proves the behaviour.
3. Wrong claims are fixed in the doc, never softened; missing evidence becomes a task.
4. `aix docs validate`; the doc's front matter gets `verified: <date>`.
