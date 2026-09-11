---
id: aix/agents/output
description: "ACME's output block: front matter, commit format with a Jira key, the task report shape."
block: true
order: 50
section: "Output"
---
Docs use the front-matter in `.aix/meta-docs/conventions/document-format.md` plus `owner:` and `verified:`.
Commits: `<type>(<scope>): <summary> [ACME-<jira> <IDs>]`; one merge request per task.
Task report: what changed · IDs touched · tests · security rows still open · reviewer lens that failed, if any · next step.
