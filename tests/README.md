# AIX test suite

Tests of the kit itself. They live here, outside the payload (`.aix/scripts/payload.py` lists what travels; `tests/`
is not in it), so no project ever receives them.

## Run

```bash
python -m unittest discover -s tests -v
```

No dependency beyond Python 3.10+. Add `AIX_TEST_NETWORK=1` to run the registry download tests (one file: `python -m unittest discover -s tests -p test_registry.py`). Windows runs the
same command with `aix.cmd`; the curses checklist test is skipped there.

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
| `helpers.py` | `run`, `install`, `upgrade`, `project_cmd`, `assert_healthy`, `make_fork`, `previous_kit`, `fixture` |
| `fixtures/` | small template folders: a flat project, a three-project folder, a bare custom layer ([README](fixtures/README.md)) |
| `test_kit.py` | the checkout: install, doctor, validate, graph gate on the scripts, selftests, help |
| `test_install.py` | a fresh install: exactly the payload, manifest, links and pointers, idempotent, `--copy`, collisions |
| `test_upgrade.py` | from the previous release: files added, profile/instructions/`code_roots`/notes kept, local edit flagged |
| `test_layers.py` | `.aix/org/` and `.aix/custom/`: fork install, a fork edit reaching the project, `--from`, `--from-org`, `--from-custom` |
| `test_instructions.py` | enable/disable, rendered Copilot and Cursor files, AGENTS.md blocks, profiles, `aix rules` |
| `test_skills.py` | list, info, `use`/`default`, disable/enable, registry listing |
| `test_code.py` | `aix code find` (list, yes, the checklist through a pseudo-terminal), every code tool, hidden folders |
| `test_migration.py` | a 1.x layout generated from a fresh install migrates on upgrade |
| `test_registry.py` | download of a classed and a bare registry skill (network only) |

## Not covered

Whether VS Code, Claude Code, Cursor, Gemini CLI or opencode actually pick up the rendered files and trigger the
skills. That is a manual check per runtime.
