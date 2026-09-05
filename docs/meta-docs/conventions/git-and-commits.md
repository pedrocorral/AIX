---
id: META-CONV-GIT
title: Git and commit conventions
---
# Git and commits
- Branch per task: `task/TASK-0042-short-title`.
- Commit: `<type>(<scope>): <summary> [IDs]` — types: feat, fix, test, docs, sec, refactor, chore.
  Example: `feat(auth): password reset flow [FR-AUTH-003, TS-AUTH-011, TASK-0042]`.
- A commit that changes `docs/requirements/` must reference an ADR or be type `docs` on a `draft` requirement.
- Never force-push shared branches; never rewrite history containing ADRs.
- PR description = task file's goal + DoD checklist copy.
