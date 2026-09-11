---
name: workflow-setup-tracker
description: Configure the project's issue tracker for the workflow skills: labels, states, the local fallback, and where tasks and tickets are mirrored; use once per repository or when moving trackers.
disable-model-invocation: true
---
# workflow-setup-tracker

Reading budget: `references/trackers.md`; the tracker's settings page or CLI.

## Procedure
1. Choose the tracker: GitHub Issues, GitLab Issues, or local (the AIX road-map only). Record it in `.aix/config.yaml` under `tracker:`.
2. Create the label vocabulary from `workflow-triage` (`references/labels.md` there) with the same names everywhere.
3. Decide the mirror rule: tasks live in the road-map; tickets in the tracker link to TASK ids; never two sources of truth for status.
4. Verify with one round trip: create a ticket, create its task, close both.

## Outputs
A configured tracker, the config line, one verified round trip.
