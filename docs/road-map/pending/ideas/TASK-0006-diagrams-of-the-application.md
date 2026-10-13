---
id: TASK-0006
title: Diagrams of the application
status: pending             # pending | going-on | blocked | completed
created: 2026-10-09
completed:
requirements: []            # FR-*/NFR-* this task delivers or touches
tests: []                   # TS-* to automate
security: []                # VUL-* to address
context_files: []           # THE ONLY files an agent must read to work on this task
scope: []                   # paths/globs this task will change (aix task start warns when two going-on tasks overlap)
owner:                      # the seat that holds it (agent-001 ...), signed by aix task start
claimed:
claimed_by:                 # tool user@host behind the seat at that moment (stays after the seat is released)
policy:                     # a cycle for this task only (hotfix, release, ...); empty = the project's (aix policy)
---
# TASK-0006 — Diagrams of the application

## Goal (one sentence)
Draw diagrams of an application built with AIX (its modules, isolations and frontiers, call paths) from the graph the kit already builds, or with the Python library `diagrams` (mingrammer, https://github.com/mingrammer/diagrams) if it fits.
## Plan
- [x] Analyse `diagrams` (mingrammer) against what the kit needs: no dependency in projects, five languages, output in Markdown or a static page. To verify in the analysis (from memory, not checked): it is "diagrams as code" for system architecture (cloud, Kubernetes, on-premise icons), renders through Graphviz (the `dot` binary must be installed), and accepts custom nodes.
- [ ] List the diagrams worth having: module tree with frontiers, isolation map, call paths of a function (`aix code tests --priority`), dependency cycles.
- [ ] Decide: use the library, generate a text format the library or GitHub renders (Mermaid, Graphviz DOT), or both.
## Progress log (append-only, newest last)
- 2026-10-09: noted at the user's request after 2.23.0; the user named the library: `diagrams` (mingrammer).
- 2026-10-10: analysed `diagrams` 0.25.1 (MIT, Python ~=3.9) in a scratch venv. It installs 14 packages (`pre-commit` and
  `virtualenv` among them, unused for drawing) and needs the Graphviz `dot` binary. It drew the five-language test project
  (clusters per root, HIDDEN edges red) in 0.2 s and ripgrep (84 files, 249 edges) in 1.1 s, a 4281 x 11573 px picture
  nobody can read: a file-level view is useless on a real project, whatever draws it. The SVG links each icon by an
  absolute path into site-packages (broken on any other machine; PNG is self-contained); two runs differ in random node
  ids (every regeneration is a diff). Icons per language are decoration; ABAP has none. It has 2 457 icons for cloud,
  Kubernetes, on-premise (Postgres, Redis, nginx, Kafka...) and a C4 set: that is where it fits.
- 2026-10-10: prototype run on six projects (the five-language test project, full-stack-fastapi-template, ripgrep,
  juice-shop, spring-petclinic, terragoat): 20 Mermaid diagrams, 0.1 to 7.8 s per project, identical text on a
  second run, all 20 rendered without a syntax error. Views: isolation map (declared, or proposed), modules and their
  tests, call paths into the first function to test, compose services (development and production overlay merged
  as docker compose does), Terraform resources and their references. Published for the user as a private artifact
  (https://claude.ai/artifact/3iuKyi5jpQMrFpLn8aRTuh). Found on the way: the `aix code tests` crash on root files
  and lists of maps in the YAML reader (2.23.2).
## Files changed (keep current)
-
## Verification performed (command → result, newest last)
-
## Exact next actions
1.
## Decisions / open questions
- The library is `diagrams` by mingrammer (named by the user, 2026-10-09). Open: it suits architecture views (services, infrastructure); whether it suits module-level views (frontiers, call paths) is what the analysis decides.
- Recommendation (2026-10-10, to be decided by the user): code views (isolations and frontiers, module tree with tests, call
  paths) as Mermaid written by the kit into Markdown, aggregated at isolation or module level, no dependency, rendered by
  GitHub; `diagrams` only for an infrastructure view (docker-compose, Kubernetes, Terraform, which `infrarules.py` already
  reads): AIX writes a `diagrams` script the project runs where the library is installed, never a kit dependency.
## Definition of done checklist
- [ ] requirements referenced are `implemented`  - [ ] tests automated & green
- [ ] security entries updated  - [ ] docs INDEX updated  - [ ] coverage matrix regenerated
