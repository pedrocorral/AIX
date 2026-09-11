---
name: coach-questionnaire
class: coach/questionnaire
id: "@acme/questionnaire-with-defaults"
version: 1.0.0
description: Turn a decision the agent cannot make into a questionnaire for the person who can: precise questions, the options with consequences, and where the answer will be recorded; manual only.
disable-model-invocation: true
---
# @acme/questionnaire-with-defaults

ACME questionnaires carry a default per question and a date after which the default applies.
1. Decision, why the agent cannot take it, the deadline.
2. Questions with options, consequences, the default; filed under `docs/conflicts/open/`.
3. Defaults applied after the deadline are recorded as ADRs marked "by default".
