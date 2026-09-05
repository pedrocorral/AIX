---
name: core-sdd-workflow
description: Master loop for any build/change/fix/refactor/vibe-code request in an AIX repo: chains spec, test, implement, security and review skills; keeps requirements as ground truth.
---
# core-sdd-workflow (orchestrator)

Reading budget: AGENTS.md (in context) + `docs/road-map/going-on/STATE.md` + the task's `context_files`. Do not open other folders until a step requires it.

## When NOT to use
Pure questions with no code/doc change (answer directly, citing docs).

## Procedure
1. **Resume**: if STATE.md has an active task, run `core-session-resume`; else continue.
2. **Classify the request** (one line to the user): new feature / change to existing behaviour / bug / refactor / infra / docs-only / exploration ("vibe").
3. **Spec check** — `grep -rl "<keywords or IDs>" docs/requirements`.
   - Requirement exists & approved → continue.
   - Missing or draft → run `spec-write-requirement` (vibe mode allows a 1-paragraph draft) and get user approval (ask once, concisely).
   - Contradiction with code or another doc → run `core-conflict-resolution` and STOP until the user answers.
4. **Test plan** — run `testing-plan-tests` for the affected ACs (creates/extends TS files; no duplicates).
5. **Threat check** — if new endpoint/input/storage/dependency/LLM call: run `security-threat-model` (adds `expected` rows).
6. **Task** — run `core-roadmap-task` to create/start the task with `context_files` listing ONLY the FR/TS/DM/API files and code paths involved. Update STATE.md.
7. **Implement** — run `implement-feature` (it picks layer skills). Add `@implements` markers.
8. **Tests** — run the `testing-write-*` skills for each TS; mark `status: automated`; run the suite.
9. **Audit** — run `security-audit` for the categories touched in step 5.
10. **Review** — run `review-code-review` and `review-doc-drift-check` on the diff.
11. **Close** — `aix validate`, `aix coverage`, DoD checklist (`docs/meta-docs/workflow/definition-of-done.md`), `core-roadmap-task` done, `core-session-handoff`.

## Outputs
Updated requirements (if any, via ADR), TS files, task file, code with markers, tests, audit report, STATE.md.

## Reporting to the user (end of task)
5 lines: what changed; IDs touched; test result; security rows still `expected`; next task suggestion.
