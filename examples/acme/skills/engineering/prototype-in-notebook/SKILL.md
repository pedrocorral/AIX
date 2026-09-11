---
name: workflow-prototype
class: workflow/prototype
id: "@acme/prototype-in-notebook"
version: 1.0.0
description: Build a throwaway prototype to answer one design question quickly, in isolation from the product code, with the answer and the deletion recorded; use on "can we / sanity-check / spike".
---
# @acme/prototype-in-notebook

ACME prototypes live in a notebook or a single script under `prototypes/` and die within the week.
1. The question and its observable on the first line.
2. One file; real data sample; no product imports unless unavoidable.
3. Result recorded in the ADR or task; file deleted or moved to `docs/operations/spikes/` as text.
