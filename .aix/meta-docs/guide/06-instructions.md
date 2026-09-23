---
id: META-GUIDE-INSTRUCTIONS
title: Instructions and profiles
---
# 6. Instructions and profiles

## Two kinds
**Blocks** are the sections of `AGENTS.md`. The kit ships six: header, authority order, rules, navigation, session,
output. `aix install` assembles `AGENTS.md` from them, in `order`, and keeps the managed sections it renders
(`## Organisation`, `## Scoped instructions`, `## Always-on skills`) and your `## Project notes`. Do not edit the
rest of `AGENTS.md` by hand: the next install rewrites it, and `aix doctor` tells you when a section came from nowhere.

**Scoped standards** apply on their own: always (`always: true`), or when the agent works on files matching their
`applyTo` globs. The kit ships them as opt-in: `aix/frameworks/fastapi-backend`, `react-frontend`, `kedro-pipelines`,
and `aix/languages/python`, `typescript`, `java`, `rust`, each a short list of decisions (version floor, toolchain that
must pass, errors and logging, structure), meant to be replaced by your organisation's own.

Each agent gets them in its own format: Copilot as `.github/instructions/aix-*.instructions.md`, Cursor as
`.cursor/rules/aix-*.mdc`, every agent through the `## Scoped instructions` section of `AGENTS.md`.

## Switching one
```
aix instructions                     every instruction any layer offers, with its state
aix instructions info ID             kind, scope, layer, path
aix instructions enable ID           turn an optional one on (aix/languages/rust)
aix instructions disable ID          turn any off, a block included
aix rules ...                        the same command
```
States: `active`, `optional (off)`, `disabled`, `not in profile`. The choice is `instructions:` and
`disabled_instructions:` in `.aix/config.yaml`; an explicit switch wins over the profile.

## Profiles
A profile is one file, `profiles/<name>.yaml`, in any layer:
```
description: FastAPI backend and React frontend monorepo
router: |
  Backend changes follow `aix/frameworks/fastapi-backend`; frontend follows `aix/frameworks/react-frontend`.
instructions: [aix/frameworks/fastapi-backend, aix/frameworks/react-frontend, aix/languages/python, aix/languages/typescript]
skills:
  implement/endpoint: "@acme/django-endpoint"
```
`router` lands in the `## Organisation` section of `AGENTS.md`; `instructions` are enabled; `skills` picks an
implementation per class. The kit ships `fastapi-react` and `kedro`.
```
aix profile                     list
aix profile show NAME           the file
aix profile use NAME            apply (profile: NAME in config)
aix profile off                 remove
```

## Writing your own
A file under `.aix/custom/instructions/` (or `.aix/org/instructions/` in a fork), any subfolder:
```
---
id: myteam/security/secrets-handling
description: One or two sentences: when it applies and what it demands.
applyTo: "**/*.py,**/*.env*"        or  always: true
---
# The standard, as short as it can be
```
For a block: `block: true`, `section: "The H2 title"`, `order: 60`. To replace a kit block, use its id
(`aix/agents/output`). A new id adds. A typo of a kit id is reported by `aix doctor` and `aix docs validate`.
