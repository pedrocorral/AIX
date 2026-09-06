---
id: META-CONV-READABILITY
title: Readability — function size, complexity, nesting, names
read_when: Writing or reviewing any function; when `aix code style` reports a finding.
---
# Readability

Modularity (`architecture/modularity.md`) shapes the graph between functions; this page shapes the inside of one.
The rules below have measurements behind them; the limits are in `framework.yaml` (`style:` block) and
`aix code style` enforces them with line-numbered feedback.

## Limits (per function unless noted)
| Metric | Limit | Why this number |
|---|---|---|
| Cognitive complexity | 15 | Campbell / SonarSource 2017: counts nesting and breaks in linear flow, built to measure understandability. Sonar's default. |
| Cyclomatic complexity | 10 | McCabe 1976: number of independent paths, hence tests needed. His own recommendation. |
| Nesting depth | 4 | Kernighan & Plauger; McConnell *Code Complete*: comprehension collapses beyond 3–4 levels. |
| Parameters | 5 | pylint default; McConnell's hard limit is 7; *Clean Code*: three is already many. |
| Lines | 60 | NASA/JPL *Power of 10*: one printed page. McConnell's survey: defects rise in very long routines; below ~50 lines shorter is not automatically better, so this is a ceiling, not a target. |
| File lines | 400 | one responsibility per file; longer files are usually two modules. |

## Context the limits respect
- **Tests** are sequential stories: twice the line limit; `assert` does not count as a branch; no magic-number or
  docstring advice (`assert status == 200` needs no constant).
- **Framework-mapped parameters**: a decorated function (FastAPI route, Click command, pytest fixture) has its
  parameters dictated by the framework; the parameter limit does not apply.
- **React components** must be PascalCase (`<NoteCard />`; camelCase would compile to an HTML tag): in `.jsx`/`.tsx`
  or any function returning JSX, PascalCase is correct.
- **HTTP status codes** are not magic numbers.

## Names (evidence: Lawrie et al. 2006; Butler et al. 2010; Hofmeister et al. 2017)
- Full words, not abbreviations: `customer_count`, not `cust_cnt`. Descriptive names speed defect finding by ~19 %.
- Functions are verbs (`load_orders`, `is_valid`); values are nouns; booleans read as questions (`is_`, `has_`, `can_`).
- One-letter names only for loop counters and maths.
- The language's casing: `snake_case` in Python and Rust, `camelCase` in JavaScript/TypeScript and Java, `UPPER_CASE` constants.
- Naming flaws correlate with defects (Butler): a name that looks wrong is a review finding, not a nit.

## Structure (convention from *Clean Code* and *Code Complete*)
- One job per function; if the description needs "and", split.
- One level of abstraction per function: a function either orchestrates calls or does the work, not both.
- Guard clauses and early returns instead of nested `if`s; extract the deepest block into a named function.
- Magic numbers become named constants; the name is the comment.
- A public function carries a one-line docstring or doc comment: what it does and when to call it.

## Modernise for the runtime you actually target
`aix code style` detects the runtime (pyproject `requires-python`, `.python-version`, the venv, `tsconfig` target,
`engines.node`, `Cargo.toml` rust-version/edition, `pom.xml`/Gradle) and adds advice that only that version enables:
an if/elif ladder on one value → `match` (Python 3.10+); `Optional[X]` → `X | None` (3.10+); `typing.List` → `list`
(3.9+); an `__init__` that only assigns → `@dataclass` (3.7+); `os.path` → `pathlib`; `toml` → `tomllib` (3.11+);
`a && a.b` → `a?.b` and `x !== undefined ? x : d` → `x ?? d` (ES2020+); `var` → `const`/`let` (ES2015+); a match
that only unwraps → `let … else` (Rust 1.65+); a switch with `break`s → a switch expression (Java 14+).
Same idea as pyupgrade / ruff `UP`, ESLint `ecmaVersion`, Clippy MSRV lints, OpenRewrite. Advice, never gated;
when nothing declares a version the report says so and the tier is skipped.

## Tooling
`aix code style [TARGET...]` — ranked table for a folder or file, a full card for one function
(`file:func`, `file/func`, `file::Class.method`; extension optional), `--gate` for CI (fails on limits only; names,
docstrings and magic numbers are advice). Python is measured exactly; JS/TS, Rust, Java approximately.
The stack linters enforce the same limits in the editor: see `stacks/<lang>/tooling` for the rule names.
