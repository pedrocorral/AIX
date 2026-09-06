---
name: refactor-modernise
description: Apply a `modernise` line from `aix code style` (match, X | None, builtin generics, @dataclass, pathlib, tomllib, ?., ??, const/let, let-else, switch expressions): one mechanical change, nothing else; use on any modernise line.
---
# refactor-modernise
Reading budget: the modernise line (it names the construct and the version that enables it), the function.

## When NOT to use
The report header says the runtime is "assumed" (nothing declares a version): declare it first (`requires-python`, `tsconfig` target, `rust-version`, `maven.compiler.release`), then re-run.

## Procedure
1. One construct per change; never mix with a behaviour change or a readability refactor.
2. Apply the named form: `Optional[X]` → `X | None`; `typing.List[X]` → `list[X]`; if/elif ladder on one value → `match`; assign-only `__init__` → `@dataclass`; `os.path` → `pathlib`; `toml` → `tomllib`; `a && a.b` → `a?.b`; `x !== undefined ? x : d` → `x ?? d`; `var` → `const`/`let`; unwrap-only `match` → `let … else`; `switch` with `break`s → switch expression.
3. Run the linter and the tests; the diff must be the construct and nothing more.
4. `aix code style FILE:FUNCTION`: the modernise line is gone; metrics unchanged or lower.

## Outputs
Idiomatic code for the declared runtime, no behaviour change.

## Hand-off
One commit per construct type (`refactor(scope): X | None [TASK]`).
