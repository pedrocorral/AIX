---
name: coach-scaffold-exercises
description: Create an exercise set (sections, problems, solutions, explainers) with a runnable check per problem, for onboarding or teaching a code base; use on "make exercises / onboarding kata".
---
# coach-scaffold-exercises

## Procedure
1. Goal per section (one concept each); 3–5 problems per section, increasing difficulty.
2. Layout: `exercises/<section>/<nn>-<name>/{README.md,problem.*,solution.*,explainer.md}`; a `check` script per problem that passes on the solution and fails on the problem.
3. Problems draw on this repository's domain and code, not toys.
4. Run every check on solutions (all pass) and on problems (all fail); record the run.

## Outputs
The exercise tree and the check log.
