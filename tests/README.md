# AIX test suite

Tests of the kit itself. They live here, outside the payload (`.aix/scripts/payload.py` lists what travels; `tests/`
is not in it), so no project ever receives them.

## Run

```bash
aix self-test
```

From the clone `aix self-install` set up. `aix self-test agents` runs one file, `--network` adds the registry
downloads, `-q` hides the per-test lines. The long form is `python -m unittest discover -s tests -v`.

No dependency beyond Python 3.10+. Add `AIX_TEST_NETWORK=1` to run the registry download tests (one file: `python -m unittest discover -s tests -p test_registry.py`). Windows runs the
same command with `aix.cmd`; the curses checklist test is skipped there. The suite runs only when someone runs it; there is no CI workflow.

## How a test works

Every test creates a temporary folder and works only inside it: a temporary `HOME` (so `~/.local/bin`, `~/.cache/aix`
and the person layer are never touched), `CI=1` and `AIX_NO_USER=1` (no prompts, no checklist, no person layer), and
the real launcher `.aix/bin/aix` run as a subprocess. Assertions are on the exit code, lines of output and files on
disk. The exception is `test_kit.py`, which runs `aix install`, `aix doctor` and the gates on the checkout itself,
as a developer does.

The kit is installed into the temporary folder from this checkout, from a copy of it playing an organisation's fork
(`helpers.make_fork`), or from the previous tagged release checked out as a git worktree (`helpers.previous_kit`,
skipped when git or a tag is missing).

## Files

| File | Covers |
|---|---|
| `helpers.py` | `run`, `install`, `upgrade`, `project_cmd`, `assert_healthy`, `make_fork`, `previous_kit`, `fixture`, `Terminal` (the launcher in a pseudo terminal) |
| `fixtures/` | small template folders: a flat project, a three-project folder, a bare custom layer ([README](fixtures/README.md)) |
| `test_kit.py` | the checkout: install, doctor, validate, graph gate on the scripts, selftests, help, the guide |
| `test_install.py` | a fresh install: exactly the payload, manifest, links and pointers, idempotent, `--copy`, collisions |
| `test_upgrade.py` | from the previous release: files added, profile/instructions/`code_roots`/notes kept, local edit flagged |
| `test_layers.py` | `.aix/org/` and `.aix/custom/`: fork install, a fork edit reaching the project, `--from`, `--from-org`, `--from-custom` |
| `test_instructions.py` | enable/disable, rendered Copilot and Cursor files, AGENTS.md blocks, profiles, `aix rules` |
| `test_skills.py` | list, info, `use`/`default`, disable/enable, registry listing |
| `test_code.py` | `aix code find` (list, yes, the checklist through a pseudo-terminal), every code tool, hidden folders |
| `test_migration.py` | a 1.x layout generated from a fresh install migrates on upgrade |
| `test_agents.py` | `aix agents`: list, names, aliases, only the selected folders and pointers, deselection removes AIX files and keeps a person's, `--agents` at install, upgrade keeps the line, the checklist through a pseudo-terminal |
| `test_gitignore.py` | missing lines printed without a terminal, added on `upgrade --yes` and on a y answer, once; a person's `CLAUDE.md` and `.github/skills` kept as `-bak` |
| `test_selfinstall.py` | link, profile lines per shell, idempotence, foreign file kept, stale link replaced, dry run, refusal from a project, `aix version` naming both copies |
| `test_docs_split.py` | projects seeded from `.aix/templates/docs`, the kit's own `docs/` never travels, upgrade leaves docs alone, org/custom overlay the seed and the pointer texts |
| `test_selfcommands.py` | `aix self-update`: its units (`is_git_clone`, `version_of`, `git_pull` ok and failing, `update_message`) and the command against a local origin, `aix self-test` on one file and refused from a project, `install.sh` end to end with a local repository, doctor's leftover warning |
| `test_help.py` | `aix help <topic>` is the Markdown page, aliases and sub-commands, the unknown-topic list, usage and about from the pages, a custom layer replacing a page |
| `test_java.py` | the code tools on a Maven project: same-package and wildcard references are edges, entry classes are not dead, the two-line SQL shape is a finding, runtime and modernise advice |
| `test_wrappers.py` | pass-through wrappers in Python, JS, TS, Rust and Java: 25 flagged, 30 legitimate shapes (named expressions, factories, adapters, decorated, trait and overridden methods) not; gate, table count and card |
| `test_js_taint.py` | JS/TS taint on Express, Next, React/browser, Node CLI and Koa samples: every marked line found with its CWE, every other line clean (sanitisers, parameter arrays, argument lists, constants, callbacks, scopes); accepted marker, test tag, gate count, Python untouched |
| `test_two_line.py` | assembled-then-used in Python, JS, Java and Rust: every sink kind once, the negatives (no literal, reassignment, argument list, no shell, no sink), the 40-line reach, the accepted marker, the two-line snippet |
| `test_registry.py` | download of a classed and a bare registry skill (network only) |
| `test_extended.py` | `aix self-test --extended`: every code tool on twelve real projects (`extended/projects.json`, pinned commits, cloned into `~/.cache/aix/extended/`, never into the repo): no traceback, under 120 s per tool, numbers within 10 % of `extended/expected.json` (`--record` accepts them), the documented vulnerabilities of `extended/known.json` found |

## Extended tests

`tests/extended/` holds three small files: `projects.json` (twelve projects, URL, ref, pinned commit), `expected.json`
(the recorded numbers per project and tool) and `known.json` (documented vulnerabilities of the four vulnerable-by-design
apps, verified line by line at the pinned commit, with the tool that must find each). The projects themselves live in
`~/.cache/aix/extended/<name>-<commit>/` and are never part of this repository. The test is skipped unless
`aix self-test --extended`; the first run needs the network. After a deliberate change in a tool, review the new
numbers and run `--extended --record`.

## Not covered

Whether VS Code, Claude Code, Cursor, Gemini CLI or opencode actually pick up the rendered files and trigger the
skills. That is a manual check per runtime.
