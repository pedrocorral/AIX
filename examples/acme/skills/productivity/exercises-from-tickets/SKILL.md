---
name: coach-scaffold-exercises
class: coach/scaffold-exercises
id: "@acme/exercises-from-tickets"
version: 1.0.0
description: Create an exercise set (sections, problems, solutions, explainers) with a runnable check per problem, for onboarding or teaching a code base; use on "make exercises / onboarding kata".
---
# @acme/exercises-from-tickets

ACME exercises are past tickets replayed.
1. Pick closed tasks with a clear check; strip the solution commit to make the problem.
2. Layout `exercises/<section>/<nn>-<name>/`; the original check script proves the solution.
3. Run all checks both ways; log the run.
