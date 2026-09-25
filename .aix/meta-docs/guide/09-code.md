---
id: META-GUIDE-CODE
title: The code tools
---
# 9. The code tools

All of them read the same folders: `paths.code_roots` in `.aix/config.yaml`, set by `aix code find`. When none of
the configured folders exists they scan the whole project and say so. A path on the command line narrows any of
them: `aix code style backend`. Python, JavaScript, TypeScript, Rust and Java are parsed.

## Which folders: `aix code find`
Lists every top-level folder with source files, and the root itself when files sit there, with files per language
and the project marker (`pyproject.toml`, `package.json`, `Cargo.toml`, `pom.xml`). A checklist writes the choice;
`--list` only prints, `--yes` accepts everything. `aix install` runs it at the end.

## Licences: `aix code licenses`
Reads the licence of every installed dependency from the metadata on disk and classes it. Strong copyleft,
proprietary and unknown licences fail the gate until you decide: `licenses_allow: [...]` accepts an id, `licenses_known:`
records what you read in a LICENSE file. The skill `security-audit-licenses` does the reading.

## Modularity: `aix code graph` (alias `complexity`)
Builds A, the dependency graph between modules, and B, the ideal shape of the same nodes: every node a leaf or a
composer, arcs only downward, no cycle, no hub. The distance from A to B is a list of edits with reasons: CUT an arc
that closes a cycle or points upward, SPLIT a node that is both used everywhere and orchestrating. Zero edits means
the code already has the ideal shape. Also: stable nodes, propagation cost, NCCD, the folder modularity Q.
`--functions` does the same for functions, in the four languages, and says how many calls it could resolve; `--roles` lists every
node's level and role. `--gate` fails on any CUT; `--max-distance N` caps the edits. `--report` writes
`docs/tests/dependency-graph.md`. Each edit names the refactor skill that does it: `refactor-cycle`, `refactor-hub`.

## Dead code and clones
`aix code dead` lists modules no entry point reaches and, with `--functions`, Python functions never referenced.
`aix code clones` lists duplicated functions: exact groups and near clones (`--similarity PCT`). Skills:
`refactor-dead`, `refactor-clone`.

## Readability: `aix code style`
Per function: lines, cognitive complexity, cyclomatic complexity, nesting depth, parameters, plus names, docstring
and magic numbers as advice. Limits live under `style:` in `.aix/config.yaml`, with their sources in
`readability.md`. Tests get double the line limit; decorated functions have no parameter limit; HTTP status codes are
not magic numbers. It detects the runtime version and suggests modern constructs the floor allows (`match`,
`X | None`, `?.`, `let-else`). `aix code style FILE:FUNCTION` prints one function as a card with line-numbered
advice. `--gate` fails on any function over a limit. Skills: `refactor-readability`, `refactor-modernise`.

## The shape: `aix code stats`
A terminal histogram of function sizes, or of any style metric with `--metric`, with mean, spread, percentiles,
the share over the limit, and the largest functions, files and folders.

## Security: `aix code security` and `aix code vulnerabilities`
`security` runs deterministic pattern checks mapped to the `VUL-*` rows and CWEs: findings to review, never proof.
`--audit` writes the audit report the register needs as evidence; `--gate` for CI. A line `aix: skip-security-scan`
in a file's first lines excludes it; `aix: accepted VUL-…` marks an accepted finding.
`vulnerabilities` goes deeper: Python taint paths from an input to a dangerous call, known CVEs of pinned
dependencies (OSV, needs network), secrets in git history. `--audit` writes the report.

## Reports and gates
`--report` on graph, style, security, stats and vulnerabilities writes under `docs/tests/`; those files are
generated and ignored by git. The gates, `aix code graph --gate`, `aix code style --gate`,
`aix code security --gate`, `aix docs security --gate`, exit 1 for CI.
