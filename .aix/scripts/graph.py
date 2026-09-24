#!/usr/bin/env python3
"""aix code graph|dead|clones — measure the codebase dependency graph: complexity vs ideal complexity.

Nodes are modules (files) for Python, JavaScript/TypeScript, Rust and Java, or functions/methods for Python
(`--functions`). Edges are imports / calls between project files (external packages ignored).

  stable nodes      instability I = out/(in+out) <= 0.25 (Martin): depending on them is free reuse, not counted
  complexity        edges into non-stable nodes
  ideal complexity  the transitive reduction (Aho, Garey & Ullman 1972) with cycles contracted: every dependency
                    kept, shortcuts removed, each cycle at its acyclic minimum. The baseline: lowest complexity
                    that delivers the same dependencies, achievable or not.
  reducible         (complexity - ideal) / ideal, as %. Each counted edge is listed with its bypass ("also via B").
  upward            edges into a composition root, or from a lower layer into a higher one: defects regardless
  cycles            strongly connected components with more than one node: defects
  NCCD, Q           Lakos' normalised cumulative dependency (1.0 = balanced binary tree); Newman modularity of
                    the folder partition at depths 1-3
  hubs           nodes with high fan-in AND high fan-out: changes there propagate everywhere
  propagation    average share of the graph reachable from a node (MacCormack, Rusnak & Baldwin 2006)

Static analysis is approximate for dynamic languages: unresolved imports/calls are ignored, never guessed."""
import sys
from codefiles import EXT, HUB_FAN, ROOT, default_roots
from depedges import function_graph, module_graph
from graphmetrics import STABLE_MAX, collapse_facades, is_composition_root, measure
from deadcode import render_dead
from clones import SIMILARITY, render_clones



# ---- dead code --------------------------------------------------------------------------------------------------
# ---- clones -------------------------------------------------------------------------------------------------------


# ---- report -----------------------------------------------------------------------------------------------

def _finding_lines(m) -> list:
    lines = [f"  CYCLE     {' -> '.join(c)} -> {c[0]}" for c in m["cycles"][:10]]
    lines += [f"  UPWARD    {a} -> {b}  ({why})" for a, b, why in m["upward"][:15]]
    lines += [f"  SHORTCUT  {a} -> {b}  also reached via {via}" for (a, b), via in sorted(m["shortcuts"].items())[:15]]
    for h in m["hubs"][:10]:
        note = "composition root: a hub by design" if is_composition_root(h) else "split it: keep the stable part, move the rest up"
        lines.append(f"  HUB       {h}  (in {m['fi'][h]}, out {m['fo'][h]})  {note}")
    if lines:
        lines.append("  fix with: CYCLE/UPWARD -> skill refactor-cycle; SHORTCUT -> refactor-shortcut; HUB -> refactor-hub (aix skills show NAME)")
    return lines


def render(m, level, scope):
    q = "  ".join(f"depth {d}: {v:.2f} ({k} folders)" for d, (v, k) in m["q"].items() if k > 1)
    lines = [f"Dependency graph ({level}) — {scope}", "",
             f"  nodes {m['n']}, edges {m['e']}, components {m['p']}; {m['facades']} re-export facades collapsed",
             f"  stable nodes (instability <= {STABLE_MAX}) {m['stable']}; edges into them, free reuse, not counted: {m['reuse']}",
             f"  complexity        {m['complexity']} edges (into non-stable nodes)",
             f"  ideal complexity  {m['ideal']} edges (transitive reduction: every dependency kept; cycles at their acyclic minimum)",
             f"  reducible         {m['reducible_pct']:.1f} %  ({m['reducible']} edges: {len(m['shortcuts'])} shortcuts, {m['cyc_reducible']} cycle edges; wiring from roots/tests exempt: {m['wiring']})",
             f"  cycles {len(m['cycles'])}   upward dependencies {len(m['upward'])}   hubs {len(m['hubs'])} (fan-in and fan-out both >= {HUB_FAN})",
             f"  propagation cost {m['prop']:.1f} %   NCCD {m['nccd']:.2f} (1.0 = balanced binary tree, Lakos)   modularity Q by folder {q or 'n/a'}", ""]
    return "\n".join(lines + _finding_lines(m))


def write_report(text: str):
    out = ROOT / "docs" / "tests" / "dependency-graph.md"
    out.write_text("# Dependency graph (generated — do not edit)\n\n```\n" + text + "\n```\n", encoding="utf-8")
    return out


# ---- self-test: graphs with known answers -----------------------------------------------------------------------

SELFTEST_CASES = [
    ("chain a->b->c->d", {("a", "b"), ("b", "c"), ("c", "d")}, dict(reducible=0, cycles=0)),
    ("diamond a->b->d, a->c->d", {("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")}, dict(reducible=0, cycles=0)),
    ("diamond + shortcut a->d into a stable leaf d: free reuse", {("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"), ("a", "d")}, dict(reducible=0, cycles=0, reuse=3)),
    ("diamond + shortcut a->d, d unstable (d->e, d->f)", {("a", "b"), ("a", "c"), ("b", "d"), ("c", "d"), ("a", "d"), ("d", "e"), ("d", "f")}, dict(reducible=1, cycles=0, shortcut=("a", "d"))),
    ("two-node cycle", {("a", "b"), ("b", "a"), ("a", "c")}, dict(reducible=1, cycles=1)),
    ("stable leaf reused: a->s, b->s, a->b", {("a", "s"), ("b", "s"), ("a", "b")}, dict(reducible=0, cycles=0, reuse=2)),
    ("layer skip x/controllers/r -> x/services/s -> x/models/m, r->m (m stable)",
     {("x/controllers/r.py", "x/services/s.py"), ("x/services/s.py", "x/models/m.py"), ("x/controllers/r.py", "x/models/m.py"), ("y/z.py", "x/models/m.py")},
     dict(reducible=0, cycles=0)),
    ("upward: x/models/m -> x/services/s", {("x/models/m.py", "x/services/s.py")}, dict(upward=1)),
]


def _case_result(edges, want):
    m = measure({n for e in edges for n in e}, edges)
    got = dict(reducible=m["reducible"], cycles=len(m["cycles"]), reuse=m["reuse"], upward=len(m["upward"]))
    ok = all(got[k] == v for k, v in want.items() if k != "shortcut") and ("shortcut" not in want or want["shortcut"] in m["shortcuts"])
    return ok, got


def selftest():
    failed = 0
    for name, edges, want in SELFTEST_CASES:
        ok, got = _case_result(edges, want)
        failed += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: {', '.join(f'{k}={got[k]}' for k in want if k != 'shortcut')}")
    print("selftest: " + ("all passed" if not failed else f"{failed} FAILED"))
    sys.exit(1 if failed else 0)


USAGE = "usage: aix code graph|dead|clones [PATH...] [--functions] [--similarity PCT] [--gate] [--max-reducible PCT] [--report] [--selftest]"


class _Options:
    """What `aix code graph|dead|clones` was asked."""
    def __init__(self, args):
        args = list(args)
        self.functions, self.gate, self.report = "--functions" in args, "--gate" in args, "--report" in args
        self.dead, self.clones = "--dead" in args, "--clones" in args
        self.similarity = float(_take(args, "--similarity", SIMILARITY))
        self.max_reducible = _take(args, "--max-reducible", None)
        self.max_reducible = float(self.max_reducible) if self.max_reducible is not None else None
        self.paths = [a for a in args if not a.startswith("--")] or default_roots()


def _take(args: list, flag: str, default):
    """Remove `flag VALUE` from args (in place) and return VALUE, else the default. --max-excess is an old alias."""
    for name in ([flag, "--max-excess"] if flag == "--max-reducible" else [flag]):
        if name in args:
            i = args.index(name); value = args[i + 1]; del args[i:i + 2]
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


def _graph_gate(m, max_reducible):
    bad = []
    if m["cycles"]:
        bad.append(f"{len(m['cycles'])} cycle(s)")
    if m["upward"]:
        bad.append(f"{len(m['upward'])} upward dependency(ies)")
    if max_reducible is not None and m["reducible_pct"] > max_reducible:
        bad.append(f"reducible complexity {m['reducible_pct']:.1f} % > {max_reducible:g} %")
    if bad:
        sys.exit("GATE FAILED: " + "; ".join(bad))
    print("GATE PASSED")


def main(args):
    if "--selftest" in args:
        return selftest()
    o = _Options(args)
    nodes, edges = function_graph(o.paths) if o.functions else module_graph(o.paths)
    if not nodes:
        sys.exit(f"no source files under {', '.join(o.paths)} (looked for {', '.join(EXT)})")
    if o.clones:
        text, n_exact = render_clones(o.paths, o.similarity)
        return _finish(o, text, n_exact, "exact clone group(s)")
    if o.dead:
        mn, me, _ = collapse_facades(*map(set, module_graph(o.paths)))
        text, n_dead = render_dead(mn, me, o.paths, o.functions)
        return _finish(o, text, n_dead, "dead-code candidate(s)")
    m = measure(nodes, edges)
    text = render(m, "functions" if o.functions else "modules", ", ".join(o.paths))
    print(text)
    if o.report:
        print(f"\n  wrote {write_report(text).relative_to(ROOT)}")
    if o.gate:
        _graph_gate(m, o.max_reducible)


if __name__ == "__main__":
    main(sys.argv[1:])
