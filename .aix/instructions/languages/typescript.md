---
id: aix/languages/typescript
name: "TypeScript Conventions"
description: "Use when writing or changing TypeScript or JavaScript: strictness, toolchain (eslint, prettier, vitest), modules, errors, dependencies. Decisions, not a tutorial."
applyTo: "**/*.ts,**/*.tsx,**/*.mts,**/tsconfig*.json,**/package.json"
optional: true
---
# TypeScript conventions

Decisions this codebase has made. Replace this file in your organisation layer to state yours.

## Language
- TypeScript everywhere; `.js` only for config files that the tool cannot read as `.ts`.
- `strict: true`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`; no `any` (use `unknown` and narrow), no non-null `!` outside tests, no `@ts-ignore` (use `@ts-expect-error` with a reason).
- ES modules (`"type": "module"`), named exports, no default exports except where a framework requires one (route files, pages).
- Target the Node or browser floor in `package.json` `engines` / browserslist; `aix code style --modernise` reports code older than the floor.

## Toolchain (must pass before "done")
- `eslint` with `typescript-eslint` recommended-type-checked, `import/order`, `complexity` (10), `max-params` (5), `max-depth` (4); `prettier` for formatting, no style rules in eslint.
- `vitest` (or `jest`) with `tests/` or `*.test.ts` next to the module, one test file per module; coverage threshold in the config.
- `tsc --noEmit` in CI; a single package manager with a committed lockfile.

## Errors and async
- Throw `Error` subclasses from the project's `errors` module; never throw strings; every `Promise` awaited or returned (`no-floating-promises`).
- Validate external data at the boundary (`zod`, `valibot` or generated types from OpenAPI); never trust `JSON.parse` output as a typed value.
- No `console.log` outside CLIs; a logger with levels.

## Structure
- Files under 400 lines, functions under 60 (`aix code style`); `import type` for types; no circular imports (`aix code graph --gate`).
- React components in PascalCase files; hooks start with `use`; see `aix/frameworks/react-frontend` when it applies.
