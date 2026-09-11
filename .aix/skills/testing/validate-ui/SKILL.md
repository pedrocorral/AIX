---
name: testing-validate-ui
description: Validate a UI feature or refactor in the real rendered application with reproducible evidence: a scripted run, screenshots per step, console and network clean; use after any frontend change.
---
# testing-validate-ui

Reading budget: the TS-* functional spec, the running app's URL, `.aix/meta-docs/testing/levels.md`.

## Procedure
1. Start the app (`aix`'s `run` skill or the project's command); note version/commit.
2. Script the journey (Playwright or the browser tool): each step = action + assertion + screenshot named `<TS>-<step>.png`.
3. Evidence: screenshots, console errors (must be none), failed network requests (none), the test output.
4. Attach the evidence path to the TS (`status: automated` only if the script runs in CI; else `manual` with the run recorded).
5. Any mismatch with the requirement → `core-conflict-resolution`, not a silent UI tweak.

## Outputs
The script, the evidence folder, the TS status updated with the run reference.
