---
name: coach-questionnaire
description: Turn a decision the agent cannot make into a questionnaire for the person who can: precise questions, the options with consequences, and where the answer will be recorded; manual only.
disable-model-invocation: true
---
# coach-questionnaire

## Procedure
1. State the decision and why the agent cannot take it (missing authority, missing fact).
2. Each question: what is asked, the options, the consequence of each, the default if unanswered.
3. Write it to `docs/conflicts/open/` (if it blocks a requirement) or to the task; ask the user to send it to the decider.
4. When the answers come back: ADR (`spec-write-adr`) or requirement update; close the conflict.

## Outputs
The questionnaire file; the decision recorded when answered.
