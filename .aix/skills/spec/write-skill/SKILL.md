---
name: spec-write-skill
description: Review or write an Agent Skill (SKILL.md) with a reliable trigger description, progressive disclosure, checkable completion and the AIX sections; use on "write/improve a skill".
disable-model-invocation: true
---
# spec-write-skill

Reading budget: `.aix/templates/skill/SKILL.md`, the skill under review, `.aix/meta-docs/conventions/cli.md` (classes section).

## When NOT to use
The request is a document for humans (use `spec-plain-language`) or an instruction block (use `spec-write-for-agents`).

## Procedure
1. **Trigger first**: the `description` names the situations and the words a user would say (≥ 40 chars, ≤ 2 lines); no marketing.
2. **Class**: pick the class it implements (`class:` when the folder name differs); `name:` = class flat name; `id:`/`version:` for the implementation.
3. **Sections**: When NOT to use · Inputs · Procedure (numbered, each step has a verifiable result) · Outputs · Hand-off. Reading budget on top.
4. **Progressive disclosure**: the body ≤ 60 lines; long material goes to `references/`, deterministic checks to `scripts/`.
5. **Completion is checkable**: every step ends with a command, a file, or a question to the user, never "consider".
6. Run `aix docs validate` (name/class rule, description length); `aix skills info NAME` shows it resolved.

## Outputs
A SKILL.md that passes validate and can be triggered by its description alone.
