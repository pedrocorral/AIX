---
id: TASK-0002
title: Support Antigravity and Gemini CLI runtimes
status: completed
created: 2026-09-05
completed: 2026-09-05
requirements: []            # kit change, no app requirement
tests: []
security: []
context_files: [scripts/install_skills.py, scripts/extern.py, scripts/doctor.py, GEMINI.md, docs/meta-docs/conventions/cli.md]
---
# TASK-0002 — Support Antigravity and Gemini CLI runtimes

## Goal (one sentence)
Make an AIX project work out of the box in Google Antigravity and Gemini CLI, with the same skills and the same always-on wiring as the other runtimes.

## Plan
- [x] Verify (official docs, 2026-09-05) where each tool reads skills and instructions:
      Antigravity → `.agents/skills` (default; `.agent/skills` legacy) and `AGENTS.md` directly (since 1.20.5).
      Gemini CLI → `.gemini/skills` or the `.agents/skills` alias (alias wins on a name clash); context file `GEMINI.md`.
- [x] Decide: no new skill target (both already read `.agents/skills`); add a `GEMINI.md` pointer only. Recorded as K11 in `AIX-DEVELOPMENT.md` §8.
- [x] `GEMINI.md` at the root (committed) pointing at `AGENTS.md`; added to `KIT_PAYLOAD`; `aix install` creates it when missing.
- [x] `extern.ALWAYS_FILES` gains `GEMINI.md` so `--always` / `aix skills always` wires Gemini CLI too.
- [x] `aix doctor` checks `GEMINI.md` exists and points at `AGENTS.md`.
- [x] Docs: README, `conventions/cli.md` always-on table, `framework.yaml` comment, `aix about`/help text, CHANGELOG, `AIX-DEVELOPMENT.md` §4 runtime facts.

## Progress log (append-only, newest last)
- 2026-09-05: created; runtime facts verified against antigravity.google/docs and geminicli.com/docs; implementation and smoke tests done in one session.

## Files changed (keep current)
- `GEMINI.md` (new) · `scripts/install_skills.py` · `scripts/extern.py` · `scripts/doctor.py` · `scripts/skills.py` (comment) · `scripts/aix.py` (help/about text)
- `framework.yaml` (comment) · `README.md` · `docs/meta-docs/conventions/cli.md` · `CHANGELOG.md` · `AIX-DEVELOPMENT.md` (§4, §8 K11)

## Verification performed (command → result, newest last)
- `./aix install && ./aix validate` → 36 skills linked; 0 errors, 0 warnings
- `./aix doctor` → installation healthy; with `GEMINI.md` renamed away → `PROBLEM GEMINI.md missing or not pointing at AGENTS.md`
- `./aix coverage && ./aix task list` → ok
- `aix install --into <scratch> --merge-all` → `added: GEMINI.md`; `AIX-DEVELOPMENT.md` not copied; `aix doctor` healthy in the target
- `extern.mark_always("testskill", True/False)` → `## Always-on skills` section written to and removed from all four pointer files, `GEMINI.md` intro names `.agents/skills/<name>/SKILL.md`

## Exact next actions
1. Review and commit (`feat(install): Antigravity and Gemini CLI support via GEMINI.md pointer [TASK-0002]`).
2. Decide whether kit-development tasks should live in `docs/road-map/` at all: this file ships in the `--into` payload with `docs/`, and `STATE.md` pointed at it while active (see AIX-DEVELOPMENT.md §9, which says kit work has no STATE.md). Either delete it before shipping or add a kit-only bucket excluded from `KIT_PAYLOAD`.
3. Optional: bump `framework.yaml` to 1.4.0 with the rest of the Unreleased changelog.

## Decisions / open questions
- No `.gemini/skills` target: redundant with `.agents/skills`, which Gemini CLI prefers anyway (K11).
- No `.agents/rules/` file for Antigravity: it reads `AGENTS.md` directly, so a rules file would be a second copy.
- Pre-existing bug found, not fixed here: `aix skills always|on-demand NAME` rejects built-in skills (`known_skill` matches folder names, not flat names, so `core-find-doc` is "unknown"); only extern skills work.

## Definition of done checklist
- [x] requirements referenced are `implemented` (none)  - [x] tests automated & green (smoke tests above)
- [x] security entries updated (none)  - [x] docs INDEX updated (no new docs file)  - [x] coverage matrix regenerated
