---
name: workflow-setup-tracker
class: workflow/setup-tracker
id: "@acme/tracker-gitlab-first"
version: 1.0.0
description: Configure the project's issue tracker for the workflow skills: labels, states, the local fallback, and where tasks and tickets are mirrored; use once per repository or when moving trackers.
disable-model-invocation: true
---
# @acme/tracker-gitlab-first

ACME uses GitLab issues with the road-map as the source of truth for status.
1. `glab label create` for the vocabulary; boards per bucket (next, backlog, blocked).
2. Every issue body starts with its TASK id; the task file links back.
3. One round trip verified; `tracker: gitlab` recorded in config.
