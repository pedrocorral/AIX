---
id: TS-KIT-001
title: The kit's automated suite
status: automated
---
# The kit's automated suite
Run: `aix self-test` (long form `python -m unittest discover -s tests`). Every test works in a temporary folder with
its own HOME, no prompts, the real launcher as a subprocess. Details: `tests/README.md` at the repo root.

| File | Proves |
|---|---|
| `test_kit.py` | the checkout installs, doctor and validate pass, the scripts pass the graph gate, selftests |
| `test_install.py` | exactly the payload arrives, manifest, links and pointers, idempotence, `--copy`, collisions |
| `test_upgrade.py` | upgrade from the previous release keeps the project's choices, adds files, flags local edits |
| `test_layers.py` | `org/` and `custom/`: fork install, fork edit reaching a project, `--from`, `--from-org`, `--from-custom` |
| `test_instructions.py` | enable/disable, rendered files, AGENTS.md blocks, profiles, `aix rules` |
| `test_skills.py` | list, info, `use`/`default`, disable/enable, registry listing |
| `test_code.py` | `aix code find` and the code tools, hidden folders, the checklist through a pty |
| `test_migration.py` | a 1.x layout migrates on upgrade |
| `test_agents.py` | agent selection, deselection, backups, `--agents`, upgrade, checklist |
| `test_gitignore.py` | the .gitignore lines and the `-bak` backups |
| `test_selfinstall.py` | link, shell profiles, idempotence, dry run, refusal, `aix version` |
| `test_selfcommands.py` | `self-update` units and command, `self-test`, `install.sh`, doctor leftovers |
| `test_help.py` | the help pages: Markdown per topic, aliases, unknown topic, usage/about, a layer replacing a page |
| `test_java.py` | Java: references without an import are edges, entry classes live, SQL assembled then executed is found |
| `test_wrappers.py` | pass-through wrappers found and legitimate shapes left alone, in five languages |
| `test_js_taint.py` | JS/TS taint: 40 marked sinks found across five frameworks, the negatives clean, tags and gate |
| `test_two_line.py` | a string assembled on one line and used by a dangerous call later is found, in four languages; the negatives stay clean |
| `test_registry.py` | registry downloads (network) |
| `test_dead.py` | dead code and clones on the shapes real projects have: conventions, containers, nested roots, re-exports |
| `test_hygiene.py` | leftovers, swallowed exceptions and known bugs found, the legitimate shapes left alone, in four languages |
| `test_ideal.py` | B built from A with known answers; the distance and its edits in the report and the gate |
| `test_funcgraph.py` | function-level graphs for JS/TS, Rust and Java with known answers |
| `test_extended.py` | the code tools on twelve real projects from a cache outside the repo (`aix self-test --extended`): no crash, time limits, recorded numbers, documented vulnerabilities found |

Not covered: planted findings for `code security|vulnerabilities|dead|clones`; `aix task`; the docs gates; always-on
wiring; the person layer; macOS and Windows (never run); the agents actually reading the files.
