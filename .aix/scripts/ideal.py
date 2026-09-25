"""Leaf: the ideal graph B of a dependency graph A, and the distance between them.

The principle (architecture/modularity.md): every node is a leaf (does work, calls nothing that changes) or a
composer (wires leaves and lower composers); arcs go only downward; no cycle; no hub. B is built from A's own nodes:
  1. every cycle is broken at the fewest arcs a greedy ordering finds (Eades, Lin & Smyth 1993);
  2. every upward arc (into a composition root, or from a lower layer to a higher one) is cut;
  3. every node gets a level: leaves are 0, a composer is one above the highest node it calls;
  4. a hub (fan-in and fan-out both >= HUB_FAN, not a composition root) is split into a leaf part that keeps the
     callers and a composer part that keeps the calls.
The distance A -> B is the number of edits (cuts and splits); each is listed with its reason. A shortcut
(A -> C next to A -> B -> C) is not an edit: a downward arc is legitimate however many paths reach it.
What B does not know: calls A could not resolve are absent from both graphs, and roles come from shape, not from
meaning; a split names where the shape breaks, the reader decides the cut."""
from collections import defaultdict

from graphmetrics import HUB_FAN, degrees, is_composition_root, is_root_or_test, sccs, upward_edges


def _order(nodes: list, edges: set) -> list:
    """Eades-Lin-Smyth: sinks go last, sources first, else the node with the largest out-in difference; arcs that
    point backwards in this order are the feedback set that breaks every cycle."""
    remaining, out, inn = set(nodes), defaultdict(set), defaultdict(set)
    for a, b in edges:
        out[a].add(b); inn[b].add(a)
    head, tail = [], []
    while remaining:
        sinks = [n for n in remaining if not (out[n] & remaining)]
        sources = [n for n in remaining if not (inn[n] & remaining) and n not in sinks]
        if sinks or sources:
            tail = sorted(sinks) + tail; head += sorted(sources)
            remaining -= set(sinks) | set(sources)
            continue
        pick = max(sorted(remaining), key=lambda n: len(out[n] & remaining) - len(inn[n] & remaining))
        head.append(pick); remaining.discard(pick)
    return head + tail


def cycle_cuts(nodes, edges) -> dict:
    """arc -> the cycle it closes (its member nodes), for the arcs B removes to become acyclic."""
    cuts = {}
    for comp in sccs(nodes, edges):
        members = set(comp)
        inside = {(a, b) for a, b in edges if a in members and b in members}
        pos = {n: i for i, n in enumerate(_order(comp, inside))}
        for a, b in sorted(inside):
            if pos[a] > pos[b]:
                cuts[(a, b)] = comp
    return cuts


def levels(nodes, dag_edges) -> dict:
    """node -> level: 0 for a leaf, else 1 + the highest level it calls (longest path from the leaves)."""
    out = defaultdict(set)
    for a, b in dag_edges:
        out[a].add(b)
    memo = {}

    def level(n):
        if n not in memo:
            memo[n] = 0 if not out[n] else 1 + max(level(m) for m in out[n])
        return memo[n]
    return {n: level(n) for n in nodes}


def role(n: str, fi: int, fo: int) -> str:
    """leaf: calls nothing; root: a composition root, a test, or nothing calls it; hub: both used everywhere and
    orchestrating (a root is a hub by design, not a defect); composer: the rest."""
    if fo == 0:
        return "leaf"
    if is_composition_root(n) or is_root_or_test(n) or fi == 0:
        return "root"
    return "hub" if fi >= HUB_FAN and fo >= HUB_FAN else "composer"


def _split(hubs: set, edges: set) -> set:
    """B's arcs once every hub is two nodes: callers reach `X (leaf)`, `X (composer)` keeps the calls and uses the leaf."""
    out = set()
    for a, b in edges:
        out.add((f"{a} (composer)" if a in hubs else a, f"{b} (leaf)" if b in hubs else b))
    return out | {(f"{h} (composer)", f"{h} (leaf)") for h in hubs}


def build(nodes, edges) -> dict:
    """A -> B with the edit list. Keys: cuts {arc: reason}, splits {node: (fan-in, fan-out)}, roles {node: role in A},
    levels {node: level in B}, b_nodes, b_edges, distance."""
    nodes, edges = set(nodes), set(edges)
    cuts = {arc: f"closes a cycle among {len(comp)} nodes: {', '.join(comp[:4])}{', ...' if len(comp) > 4 else ''}" for arc, comp in cycle_cuts(nodes, edges).items()}
    for a, b, why in upward_edges(edges - set(cuts)):
        cuts[(a, b)] = f"upward: {why}"
    dag = edges - set(cuts)
    fi, fo = degrees(dag)
    roles = {n: role(n, fi[n], fo[n]) for n in nodes}
    hubs = {n for n, r in roles.items() if r == "hub"}
    b_edges = _split(hubs, dag)
    b_nodes = (nodes - hubs) | {f"{h} (leaf)" for h in hubs} | {f"{h} (composer)" for h in hubs}
    return dict(cuts=cuts, splits={h: (fi[h], fo[h]) for h in hubs}, roles=roles, levels=levels(b_nodes, b_edges),
                b_nodes=b_nodes, b_edges=b_edges, distance=len(cuts) + len(hubs))


def edit_lines(b: dict, limit: int = 40) -> list:
    """The edits, cuts first (defects), then splits."""
    lines = [f"  CUT    {a} -> {x}  ({why})" for (a, x), why in sorted(b["cuts"].items())]
    lines += [f"  SPLIT  {h}  (in {fi}, out {fo}): keep the work as a leaf, move the calls to a composer above it" for h, (fi, fo) in sorted(b["splits"].items())]
    if len(lines) > limit:
        lines = lines[:limit] + [f"  ... {len(lines) - limit} more edits"]
    return lines


def summary_line(b: dict) -> str:
    depth = max(b["levels"].values(), default=0)
    kinds = defaultdict(int)
    for r in b["roles"].values():
        kinds[r] += 1
    n_cycle = sum(1 for why in b["cuts"].values() if why.startswith("closes"))
    return (f"  B (ideal: leaves and composers, arcs downward, no cycle, no hub): nodes {len(b['b_nodes'])}, arcs {len(b['b_edges'])}, depth {depth}; "
            f"in A: leaves {kinds['leaf']}, composers {kinds['composer']}, roots {kinds['root']}, hubs {kinds['hub']}\n"
            f"  distance A -> B: {b['distance']} edits  (cuts: {n_cycle} cycle, {len(b['cuts']) - n_cycle} upward; splits: {len(b['splits'])})")


def roles_table(b: dict, edges) -> list:
    """Every node with its role in A and its level in B, deepest first: `--roles`."""
    fi, fo = degrees(set(edges))
    rows = sorted(b["roles"], key=lambda n: (-b["levels"].get(n, b["levels"].get(f"{n} (composer)", 0)), n))
    return [f"  {b['levels'].get(n, b['levels'].get(f'{n} (composer)', 0)):>3}  {b['roles'][n]:9s} in {fi[n]:>3} out {fo[n]:>3}  {n}" for n in rows]
