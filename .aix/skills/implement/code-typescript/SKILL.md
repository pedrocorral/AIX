---
name: implement-code-typescript
description: Implement, refactor or review TypeScript with strict types, module boundaries, explicit error handling and the readability limits; use for any TypeScript or JavaScript change outside tests.
---
# implement-code-typescript

Reading budget: `.aix/meta-docs/stacks/javascript/*.md`, `conventions/readability.md`; `aix code style FILE` on the touched file.

## Procedure
1. `strict` on; no `any` (use `unknown` + narrowing); exported types for every public function.
2. Modules: one purpose per file; imports point inward (`aix code graph --gate`); no barrel re-export cycles.
3. Errors as values or typed exceptions at boundaries; never `catch {}` empty; log at the edge with ids.
4. Async: every promise awaited or returned; cancellation/abort for long calls.
5. `?.`, `??`, `const`; no `var`; readonly where possible.
6. Functions under the limits (`aix code style FILE:FUNC`); components ≤ 60 lines, hooks own the state.
7. ESLint + tsc clean; tests for the change (`testing-write-unit-tests`).

## Outputs
Code with `@implements` markers, green lint and tests, no style finding over a limit.
