---
name: testing-validate-ui
class: testing/validate-ui
id: "@acme/ui-evidence-video"
version: 1.0.0
description: Validate a UI feature or refactor in the real rendered application with reproducible evidence: a scripted run, screenshots per step, console and network clean; use after any frontend change.
---
# @acme/ui-evidence-video

ACME validates UI with a recorded run.
1. Playwright script per TS with `video: on`; assertions per step.
2. Evidence = the video, the trace, console clean, network clean, attached under `docs/tests/evidence/<TS>/`.
3. TS automated only when the script runs in CI.
