---
name: spec-write-skill
class: spec/write-skill
id: "@acme/skill-review-checklist"
version: 1.0.0
description: Review or write an Agent Skill (SKILL.md) with a reliable trigger description, progressive disclosure, checkable completion and the AIX sections; use on "write/improve a skill".
disable-model-invocation: true
---
# @acme/skill-review-checklist

ACME reviews skills against a ten-line checklist: trigger words present, class named, name equals class, ≤ 60 lines, every step checkable, references separated, no duplicated meta-doc text, validate passes, `aix skills info` resolves it, description identical across implementations.
