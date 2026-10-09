#!/usr/bin/env python3
"""aix code affected — the test files a change can break: every test that reaches a changed file through the
import graph (depedges, the graph `aix code graph` reads), so an agent runs those and not the whole suite.

  aix code affected                 the change against HEAD (staged, unstaged and untracked files)
  aix code affected --base REF      against a commit or branch (`--base main` for a whole branch)
  aix code affected --plain         only the test paths, one per line (`pytest $(aix code affected --plain)`)

A changed test file is affected itself. A changed source file that no test reaches is listed: nothing guards it.
With an isolation declaration the tests are grouped by the isolation of the changed code. What the graph cannot
see, a test cannot be selected by: a fixture loaded by name, a plugin, a file read at run time. Run the whole suite
before a release."""
import subprocess, sys
from collections import defaultdict

from codefiles import ROOT, default_roots
from depedges import module_graph
from graphmetrics import is_test
from guard import checked

USAGE = "usage: aix code affected [PATH...] [--base REF] [--plain]"


def changed_files(base: str) -> list:
    """Paths changed against `base` (committed, staged, unstaged) plus untracked ones, relative to the project."""
    def git(*args):
        r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"git {' '.join(args)}: {r.stderr.strip() or 'failed'} (aix code affected needs a git repository)")
        return [l for l in r.stdout.splitlines() if l.strip()]
    return sorted(set(git("diff", "--name-only", base)) | set(git("ls-files", "--others", "--exclude-standard")))


def dependents(nodes: set, edges: set, start: set) -> dict:
    """node -> the changed file it depends on (directly or not), for every node that reaches one of `start`."""
    users = defaultdict(set)
    for a, b in edges:
        users[b].add(a)
    reached, todo = {n: n for n in start if n in nodes}, [n for n in start if n in nodes]
    while todo:
        n = todo.pop()
        for u in users[n]:
            if u not in reached:
                reached[u] = reached[n]
                todo.append(u)
    return reached


def affected(paths: list, base: str) -> tuple:
    """(tests -> the changed file that reaches them, changed source files no test reaches, changed files outside the graph)."""
    nodes, edges = module_graph(paths)
    changed = changed_files(base)
    inside = {f for f in changed if f in nodes}
    reached = dependents(nodes, edges, inside)
    tests = {n: why for n, why in reached.items() if is_test(n)}
    guarded = set(tests.values())
    unguarded = sorted(f for f in inside if not is_test(f) and f not in guarded)
    return tests, unguarded, sorted(set(changed) - inside)


def _grouped(tests: dict) -> list:
    """Lines of the tests, under the isolation of the changed file that reaches them (when the project declares any)."""
    import isodecl
    d = isodecl.load(ROOT)
    groups = defaultdict(list)
    for t, why in sorted(tests.items()):
        key = (d.owner_of(why) if d and d.owner_of(why) else None) or why
        groups[key].append(t)
    return [line for key, ts in sorted(groups.items()) for line in [f"  {key}:"] + [f"    {t}" for t in ts]]


def _base(args: list) -> str:
    """The value of `--base REF` (removed from args), else HEAD."""
    if "--base" not in args:
        return "HEAD"
    at = args.index("--base")
    if at + 1 >= len(args):
        sys.exit(USAGE)
    base = args[at + 1]
    del args[at:at + 2]
    return base


@checked
def main(args: list):
    args = list(args)
    base = _base(args)
    plain = "--plain" in args
    paths = [a for a in args if not a.startswith("--")] or default_roots()
    tests, unguarded, outside = affected(paths, base)
    if plain:
        print("\n".join(sorted(tests)))
        return
    print(f"Affected tests against {base}: {len(tests)} test file(s) reach the change")
    print("\n".join(_grouped(tests)) if tests else "  none")
    if unguarded:
        print("\n  no test reaches these changed files (nothing guards them):\n" + "\n".join(f"    {f}" for f in unguarded))
    if outside:
        print(f"\n  {len(outside)} changed file(s) are not code the graph reads (docs, config, assets): run the suite if they matter")


if __name__ == "__main__":
    main(sys.argv[1:])
