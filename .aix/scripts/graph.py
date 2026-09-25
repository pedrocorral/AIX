#!/usr/bin/env python3
"""aix code graph|dead|clones — the dependency graph of the code (A), the ideal graph built on the same nodes (B),
and the distance between them.

Nodes are modules (files) for Python, JavaScript/TypeScript, Rust and Java, or functions/methods for Python
(`--functions`, calls resolved by name). Edges are imports / calls between project files; external packages and
unresolved calls are ignored, never guessed, and the report says how many calls it could resolve.

  B                 the same nodes arranged by the principle in architecture/modularity.md: every node a leaf or a
                    composer, arcs only downward, no cycle, no hub (ideal.py)
  distance A -> B   the edits that turn A into B: CUT an arc that closes a cycle or points upward, SPLIT a hub
                    into a leaf and a composer. Listed one by one with the reason. A shortcut is not an edit.
  stable nodes      instability I = out/(in+out) <= 0.25 (Martin): depending on them is free reuse
  hubs, NCCD, Q     fan-in AND fan-out high; Lakos' normalised cumulative dependency; Newman modularity by folder
  propagation       average share of the graph reachable from a node (MacCormack, Rusnak & Baldwin 2006)

What B does not know: calls A could not resolve are absent from both graphs, and roles come from shape, not from
meaning: a SPLIT says where the shape breaks, the reader decides the cut."""
import sys
from codefiles import EXT, HUB_FAN, ROOT, default_roots
import ideal
from depedges import module_graph
from pyfuncgraph import RESOLUTION, function_graph
from funcgraph import function_graph_tokens
from graphmetrics import STABLE_MAX, measure
from deadcode import render_dead
from clones import SIMILARITY, render_clones



# ---- dead code --------------------------------------------------------------------------------------------------
# ---- clones -------------------------------------------------------------------------------------------------------


# ---- report -----------------------------------------------------------------------------------------------

def _shape_lines(m) -> list:
    q = "  ".join(f"depth {d}: {v:.2f} ({k} folders)" for d, (v, k) in m["q"].items() if k > 1)
    return [f"  stable nodes (instability <= {STABLE_MAX}) {m['stable']}; edges into them, free reuse: {m['reuse']}; edges into nodes that change: {m['complexity']}",
            f"  cycles {len(m['cycles'])}   upward dependencies {len(m['upward'])}   hubs {len(m['hubs'])} (fan-in and fan-out both >= {HUB_FAN})",
            f"  propagation cost {m['prop']:.1f} %   NCCD {m['nccd']:.2f} (1.0 = balanced binary tree, Lakos)   modularity Q by folder {q or 'n/a'}"]


def _a_line(m, functions: bool) -> str:
    line = f"  A (the code): nodes {m['n']}, edges {m['e']}, components {m['p']}; {m['facades']} re-export facades collapsed"
    if functions:
        seen, matched = RESOLUTION["seen"], RESOLUTION["matched"]
        line += f"; resolved calls {matched} of {seen} ({matched / seen * 100 if seen else 0:.0f} %): the rest are absent from A and B"
    return line


def render(m, b: dict, functions: bool, scope: str):
    level = "functions (calls resolved by name)" if functions else "modules"
    lines = [f"Dependency graph ({level}) — {scope}", "", _a_line(m, functions), ideal.summary_line(b), "", *_shape_lines(m), ""]
    edits = ideal.edit_lines(b)
    if edits:
        lines += ["  EDITS (do these and A is B; cuts are defects, splits are design):", *edits,
                  "  fix with: CUT -> skill refactor-cycle; SPLIT -> refactor-hub (aix skills show NAME)"]
    else:
        lines.append("  no edits: A already has the ideal shape")
    lines.append("  B does not know: calls A could not resolve (absent from both graphs), and meaning: a SPLIT says where the shape breaks, you decide the cut.")
    return "\n".join(lines)


def write_report(text: str):
    out = ROOT / "docs" / "tests" / "dependency-graph.md"
    out.write_text("# Dependency graph (generated — do not edit)\n\n```\n" + text + "\n```\n", encoding="utf-8")
    return out


# ---- self-test: graphs with known answers -----------------------------------------------------------------------

SELFTEST_CASES = [
    ("chain a->b->c->d", {("a", "b"), ("b", "c"), ("c", "d")}, dict(distance=0, cycles=0)),
    ("diamond a->b->d, a->c->d", {("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")}, dict(distance=0, cycles=0)),
    ("diamond + direct arc a->d: legitimate, not an edit", {("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"), ("a", "d"), ("d", "e"), ("d", "f")}, dict(distance=0, cycles=0)),
    ("two-node cycle: one cut", {("a", "b"), ("b", "a"), ("a", "c")}, dict(distance=1, cycles=1)),
    ("stable leaf reused: a->s, b->s, a->b", {("a", "s"), ("b", "s"), ("a", "b")}, dict(distance=0, cycles=0, reuse=2)),
    ("layer skip x/controllers/r -> x/services/s -> x/models/m, r->m (m stable)",
     {("x/controllers/r.py", "x/services/s.py"), ("x/services/s.py", "x/models/m.py"), ("x/controllers/r.py", "x/models/m.py"), ("y/z.py", "x/models/m.py")},
     dict(distance=0, cycles=0)),
    ("upward: x/models/m -> x/services/s: one cut", {("x/models/m.py", "x/services/s.py")}, dict(distance=1, upward=1)),
    ("hub h (in 3, out 3): one split", {("p", "h"), ("q", "h"), ("r", "h"), ("h", "x"), ("h", "y"), ("h", "z")}, dict(distance=1, splits=1)),
    ("composition root main.py wiring six modules: a root, never split", {("main.py", "u"), ("main.py", "v"), ("main.py", "w"), ("main.py", "x"), ("main.py", "y"), ("main.py", "z")}, dict(distance=0, splits=0)),
    ("arcs into the composition root: three upward cuts", {("p", "main.py"), ("q", "main.py"), ("main.py", "x")}, dict(distance=2, upward=2)),
]


def _case_result(edges, want):
    m = measure({n for e in edges for n in e}, edges)
    b = ideal.build(m["nodes"], m["edges"])
    got = dict(distance=b["distance"], cycles=len(m["cycles"]), reuse=m["reuse"], upward=len(m["upward"]), splits=len(b["splits"]))
    return all(got[k] == v for k, v in want.items()), got


def selftest():
    failed = 0
    for name, edges, want in SELFTEST_CASES:
        ok, got = _case_result(edges, want)
        failed += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: {', '.join(f'{k}={got[k]}' for k in want)}")
    print("selftest: " + ("all passed" if not failed else f"{failed} FAILED"))
    sys.exit(1 if failed else 0)


USAGE = "usage: aix code graph|dead|clones [PATH...] [--functions] [--roles] [--similarity PCT] [--gate] [--max-distance N] [--report] [--selftest]"


class _Options:
    """What `aix code graph|dead|clones` was asked."""
    def __init__(self, args):
        args = list(args)
        self.functions, self.gate, self.report = "--functions" in args, "--gate" in args, "--report" in args
        self.dead, self.clones, self.roles = "--dead" in args, "--clones" in args, "--roles" in args
        self.similarity = float(_take(args, "--similarity", SIMILARITY))
        self.max_distance = _take(args, "--max-distance", None)
        self.max_distance = int(self.max_distance) if self.max_distance is not None else None
        self.paths = [a for a in args if not a.startswith("--")] or default_roots()


def _take(args: list, flag: str, default):
    """Remove `flag VALUE` from args (in place) and return VALUE, else the default."""
    if flag in args:
        i = args.index(flag); value = args[i + 1]; del args[i:i + 2]
        return value
    return default


def _finish(o: _Options, text: str, n_bad: int, what: str):
    """Print, write the report, and apply the gate for the dead and clones modes."""
    print(text.lstrip("\n"))
    if o.report:
        print(f"\n  wrote {write_report(text).relative_to(ROOT)}")
    if o.gate and n_bad:
        sys.exit(f"GATE FAILED: {n_bad} {what}")
    if o.gate:
        print("GATE PASSED")


def _graph_gate(m, b: dict, max_distance):
    """Cuts are defects: any cycle or upward dependency fails. Splits are design: they fail only past --max-distance."""
    bad = []
    if m["cycles"]:
        bad.append(f"{len(m['cycles'])} cycle(s)")
    if m["upward"]:
        bad.append(f"{len(m['upward'])} upward dependency(ies)")
    if max_distance is not None and b["distance"] > max_distance:
        bad.append(f"distance A -> B {b['distance']} > {max_distance}")
    if bad:
        sys.exit("GATE FAILED: " + "; ".join(bad))
    print("GATE PASSED")


def _function_level(paths: list) -> tuple:
    """The Python call graph (by AST) and the JS/TS, Rust and Java ones (by tokens), one graph."""
    nodes, edges = function_graph(paths)          # resets the resolution count
    more_nodes, more_edges = function_graph_tokens(paths)
    return nodes | more_nodes, edges | more_edges


def main(args):
    if "--selftest" in args:
        return selftest()
    o = _Options(args)
    nodes, edges = _function_level(o.paths) if o.functions else module_graph(o.paths)
    if not nodes:
        sys.exit(f"no source files under {', '.join(o.paths)} (looked for {', '.join(EXT)})")
    if o.clones:
        text, n_exact = render_clones(o.paths, o.similarity)
        return _finish(o, text, n_exact, "exact clone group(s)")
    if o.dead:
        mn, me = module_graph(o.paths)   # reachability needs every edge: a facade's own imports keep its folder alive
        text, n_dead = render_dead(mn, me, o.paths, o.functions)
        return _finish(o, text, n_dead, "dead-code candidate(s)")
    m = measure(nodes, edges)
    b = ideal.build(m["nodes"], m["edges"])
    text = render(m, b, o.functions, ", ".join(o.paths))
    if o.roles:
        text += "\n\n  level in B, role in A, fan-in, fan-out, node:\n" + "\n".join(ideal.roles_table(b, m["edges"]))
    print(text)
    if o.report:
        print(f"\n  wrote {write_report(text).relative_to(ROOT)}")
    if o.gate:
        _graph_gate(m, b, o.max_distance)


if __name__ == "__main__":
    main(sys.argv[1:])
