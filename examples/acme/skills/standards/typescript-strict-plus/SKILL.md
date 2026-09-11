---
name: implement-code-typescript
class: implement/code-typescript
id: "@acme/typescript-strict-plus"
version: 1.0.0
description: Implement, refactor or review TypeScript with strict types, module boundaries, explicit error handling and the readability limits; use for any TypeScript or JavaScript change outside tests.
---
# @acme/typescript-strict-plus

ACME TypeScript: strict plus `noUncheckedIndexedAccess` and `exactOptionalPropertyTypes`.
1. Domain types in `packages/contracts`; components import types, never define them.
2. Data fetching only in composables/hooks; components render props.
3. Errors as discriminated unions; `never` exhaustiveness checks in every switch.
4. ESLint (ACME config) + `tsc --noEmit` before commit; `aix code style` on changed files.
