#!/usr/bin/env python3
"""aix code tests — what the tests cover, seen from the code: every module of the tree with its own tests or none,
and which functions to test first.

  (no option)       the module tree (every folder that holds code) with the test files that import it directly;
                    a module no test imports is NO TESTS. A module's own tests: a test reaching only its parent or
                    only its children does not count for it. Inline tests count (Rust `#[cfg(test)]`, ABAP
                    `FOR TESTING`). --untested prints only the untested modules; --gate fails on any.
  --priority [--top N]
                    the functions to test first, from the call graph: the call paths that end in it (every caller,
                    and every branch through every caller; a loop counts once) times cognitive complexity, the
                    functions no test calls directly first.
                    A test that calls a function directly tests it (by the call graph, or by name in a file
                    the test imports); one that reaches it only through other functions touches it.
  --affected [--base REF] [--plain]
                    the tests a change reaches (aix code affected)
  --report          also write docs/tests/tests-by-module.md

What the graph cannot see a test cannot be credited for: a test that drives the code over HTTP or a subprocess, a
fixture loaded by name, a call through an interface to an implementation the tool cannot resolve."""
import re, sys
from collections import defaultdict
from pathlib import PurePosixPath as P

from codefiles import ROOT, default_roots
from depedges import module_graph
from graphmetrics import is_test
from guard import checked

USAGE = "usage: aix code tests [PATH...] [--untested] [--gate] [--report] | --priority [--top N] | --affected [--base REF] [--plain]"
INLINE_TESTS = re.compile(r"#\[cfg\(test\)\]|\bFOR\s+TESTING\b", re.I)


# ---- modules and their tests ----------------------------------------------------------------------------------------

def folder_of(f: str) -> str:
    return str(P(f).parent)


def inline_tested(files: list) -> set:
    """Modules whose source files carry their own tests (Rust `#[cfg(test)]`, ABAP `FOR TESTING`)."""
    return {folder_of(f) for f in files if INLINE_TESTS.search((ROOT / f).read_text(encoding="utf-8", errors="replace"))}


def module_tests(files: list, edges: set) -> tuple:
    """(module -> its test files, the test files that import no module): a test belongs to every module whose
    files it imports directly."""
    sources = {f for f in files if not is_test(f)}
    tests = defaultdict(set)
    reached = set()
    for a, b in edges:
        if is_test(a) and b in sources:
            tests[folder_of(b)].add(a)
            reached.add(a)
    orphans = sorted(f for f in files if is_test(f) and f not in reached)
    return tests, orphans


def modules(files: list) -> list:
    """Every folder that holds a source file directly: the modules that need their own tests."""
    return sorted({folder_of(f) for f in files if not is_test(f)})


class Coverage:
    """The modules of the tree and what tests each one."""
    def __init__(self, files: list, edges: set):
        self.modules = modules(files)
        self.tests, self.orphans = module_tests(files, edges)
        self.inline = inline_tested([f for f in files if not is_test(f)])

    def state(self, module: str) -> str:
        n = len(self.tests.get(module, ()))
        if n:
            return f"{n} test file(s)"
        return "inline tests" if module in self.inline else "NO TESTS"

    def untested(self) -> list:
        return [m for m in self.modules if self.state(m) == "NO TESTS"]


def _tree_lines(c: Coverage) -> list:
    """The modules as an indented tree; a folder that only holds other modules is shown as their container."""
    shown, out = set(), []
    for m in c.modules:
        parts = P(m).parts
        for depth in range(len(parts)):
            folder = str(P(*parts[:depth + 1]))
            if folder in shown:
                continue
            shown.add(folder)
            label = c.state(folder) if folder in c.modules else "(holds modules only)"
            out.append(f"  {'  ' * depth}{parts[depth]}/  {label}")
    return out


def render_tree(c: Coverage) -> str:
    untested = c.untested()
    lines = [f"Tests by module — {len(c.modules)} module(s), {len(c.modules) - len(untested)} with their own tests, {len(untested)} without", ""]
    lines += _tree_lines(c)
    if c.orphans:
        lines += ["", f"  {len(c.orphans)} test file(s) import no module (end-to-end, over HTTP or a subprocess): credited to none"]
    lines += ["", "  A module with NO TESTS: write a test that imports it (skill testing-plan-tests);",
              "  what to test first inside it: aix code tests --priority"]
    return "\n".join(lines)


# ---- priority: reach x complexity -----------------------------------------------------------------------------------

def _components(nodes: list, edges: set) -> dict:
    """node -> the node standing for its loop (functions that call each other in a circle are one), else itself."""
    from graphmetrics import sccs
    comp = {n: n for n in nodes}
    for members in sccs(nodes, edges):
        comp.update({m: members[0] for m in members})
    return comp


def _topological(comps: set, links: set) -> list:
    """The loop-free graph of components, callers before the functions they call (Kahn)."""
    out, incoming = defaultdict(set), defaultdict(int)
    for y, x in links:
        out[y].add(x)
    for x in (x for y in out for x in out[y]):
        incoming[x] += 1
    order, ready = [], sorted(c for c in comps if not incoming[c])
    while ready:
        c = ready.pop()
        order.append(c)
        for x in sorted(out[c]):
            incoming[x] -= 1
            ready += [x] if not incoming[x] else []
    return order


def path_weights(nodes: list, edges: set) -> dict:
    """node -> how many call paths end in it: every caller, and every path through every caller, each branch
    counted (A calls B and C, both call D: D has 4). A loop counts as one function, so the count stays finite."""
    comp = _components(nodes, edges)
    calls = [(a, b) for a, b in edges if a in comp and b in comp and a != b]
    weight_of = _component_weights(comp, [(comp[a], comp[b]) for a, b in calls if comp[a] != comp[b]])
    weight = defaultdict(int)
    for a, b in calls:
        weight[b] += 1 + (weight_of[comp[a]] if comp[a] != comp[b] else 0)
    return {n: weight[n] for n in nodes}


def _component_weights(comp: dict, crossing: list) -> dict:
    """component -> the call paths ending in it, one per call crossing into it plus every path ending in its caller."""
    into = defaultdict(list)
    for y, x in crossing:
        into[x].append(y)
    weight_of = {}
    for c in _topological(set(comp.values()), set(crossing)):
        weight_of[c] = sum(1 + weight_of[y] for y in into[c])
    return weight_of


def _metrics(paths: list) -> dict:
    """`file:Class.func` -> cognitive complexity, for every function the style tool measures."""
    import stylemetrics
    from codefiles import source_files, rel
    out = {}
    for f in source_files(paths):
        for fx in stylemetrics.functions_in(f):
            out[f"{rel(f)}:{fx['name']}"] = fx["cognitive"]
    return out


def _file_of(node: str) -> str:
    return node.rsplit(":", 1)[0]


def priorities(paths: list) -> list:
    """(score, function, call paths ending in it, direct callers, cognitive, tested), highest first; score = (paths + 1)
    x cognitive: the function itself is one path more (an entry point is called from outside the code)."""
    import graph
    nodes, edges = graph._function_level(paths)
    code = sorted(n for n in nodes if not is_test(_file_of(n)))
    calls = {(a, b) for a, b in edges if not is_test(_file_of(a))}
    weight, cog = path_weights(code, calls), _metrics(paths)
    direct = defaultdict(int)
    for a, b in calls:
        direct[b] += 1
    by_test = {b for a, b in edges if is_test(_file_of(a))} | named_in_tests(paths, code)
    touched = _touched(nodes, edges, by_test)
    rows = [((weight[n] + 1) * cog.get(n, 0), n, weight[n], direct[n], cog.get(n, 0), _tested(n, by_test, touched)) for n in code]
    return sorted(rows, key=lambda r: (r[5] == "tested", -r[0], r[1]))


CALLED = re.compile(r"\b([A-Za-z_]\w*)\s*\(")


def named_in_tests(paths: list, functions: list) -> set:
    """Functions a test calls by name in its own code, in a file the test imports: the credit the call graph misses
    when a test calls from an anonymous callback (`it("...", () => place(cart))`)."""
    from isodata import code_of
    files, edges = module_graph(paths)
    imported = defaultdict(set)
    for a, b in edges:
        if is_test(a) and not is_test(b):
            imported[a].add(b)
    by_file = defaultdict(list)
    for n in functions:
        by_file[_file_of(n)].append(n)
    out = set()
    for test, sources in imported.items():
        called = set(CALLED.findall(code_of(ROOT / test)))
        out |= {n for s in sources for n in by_file[s] if n.rsplit(":", 1)[1].split(".")[-1] in called}
    return out


def _touched(nodes, edges, by_test: set) -> set:
    """Functions a test reaches only through other functions."""
    out, todo, adj = set(by_test), list(by_test), defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
    while todo:
        for b in adj[todo.pop()]:
            if b not in out:
                out.add(b); todo.append(b)
    return out - by_test


def _tested(n: str, by_test: set, touched: set) -> str:
    return "tested" if n in by_test else ("touched" if n in touched else "no test")


def _num(n: int) -> str:
    return f"{n:,}" if n < 10 ** 9 else f"{n:.2e}"


def render_priority(rows: list, top: int) -> str:
    shown = [r for r in rows if r[0] > 0][:top]
    lines = [f"Test priority — call paths x cognitive complexity, untested first ({len(rows)} function(s); top {len(shown)})", "",
             f"  {'score':>12}  {'paths':>10}  {'direct':>6}  {'cognitive':>9}  {'test':<8}  function"]
    lines += [f"  {_num(s):>12}  {_num(r):>10}  {d:>6}  {c:>9}  {t:<8}  {n}" for s, n, r, d, c, t in shown]
    lines += ["", "  paths: the call paths that end in it, directly or through every branch above it (a loop counts once);",
              "  score: (paths + 1) x cognitive, so a simple function called everywhere ranks below a complex one;",
              "  tested: a test calls it directly; touched: a test reaches it only through other functions."]
    return "\n".join(lines)


# ---- the command ----------------------------------------------------------------------------------------------------

def _take(args: list, flag: str, default):
    if flag not in args:
        return default
    at = args.index(flag)
    value = args[at + 1] if at + 1 < len(args) else default
    del args[at:at + 2]
    return value


def _modules_mode(args: list, paths: list):
    files, edges = module_graph(paths)
    c = Coverage(sorted(files), edges)
    text = "\n".join(f"  {m}" for m in c.untested()) if "--untested" in args else render_tree(c)
    print(text or "  every module has its own tests")
    if "--report" in args:
        out = ROOT / "docs" / "tests" / "tests-by-module.md"
        out.write_text("# Tests by module (generated — do not edit)\n\n```\n" + render_tree(c) + "\n```\n", encoding="utf-8")
        print(f"\n  wrote {out.relative_to(ROOT)}")
    if "--gate" in args:
        if c.untested():
            sys.exit(f"GATE FAILED: {len(c.untested())} module(s) without their own tests")
        print("GATE PASSED")


@checked
def main(args: list):
    args = list(args)
    if "--affected" in args:
        import affected
        return affected.main([a for a in args if a != "--affected"])
    top = int(_take(args, "--top", 20))
    paths = [a for a in args if not a.startswith("--")] or default_roots()
    if "--priority" in args:
        return print(render_priority(priorities(paths), top))
    return _modules_mode(args, paths)


if __name__ == "__main__":
    main(sys.argv[1:])
