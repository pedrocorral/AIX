---
name: refactor-readability
description: Bring a function under the `aix code style` limits (lines, cognitive/cyclomatic complexity, nesting, parameters) one metric at a time with guard clauses, extraction and parameter objects; use on any function marked OVER.
---
# refactor-readability
Reading budget: `aix code style FILE:FUNCTION` (the card), the function, `docs/meta-docs/conventions/readability.md`.

## When NOT to use
The card shows every metric `ok` (names/docstrings/magic numbers are advice: fix inline, no refactor). A test function or a decorated route over its adjusted limit is already accounted for by the tool.

## Procedure — one metric per change, worst first (the card's OVER lines)
- **nesting** → the card names the deepest block (lines a–b): invert the enclosing condition and return early, or extract lines a–b into a function named for what they do.
- **cognitive** → the card names the biggest costs (line, reason): flatten those first: guard clauses for `if` ladders, extract nested loops, replace `elif` ladders on one value with a lookup table or `match`.
- **cyclomatic** → split by case: one function per branch family, or a dispatch table.
- **lines** → extract the deepest block first (the card names it), then any block with its own comment header.
- **parameters** → group the related ones into one object (dataclass / struct / options); if unrelated, the function does two jobs: split.
After each step: `aix code style FILE:FUNCTION` again; stop when all metrics are `ok`; every extracted function gets a name, a docstring and stays a leaf (no new upward dependency: `aix code graph --gate`).
Tests: run the domain's tests after every step; if a step needs a test change other than renaming, revert it.

## Outputs
The card all `ok`, extracted functions named and documented, tests green.

## Hand-off
Progress entry: the metrics before/after, the functions extracted.
