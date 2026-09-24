"""Leaf: the numbers of a dependency graph. Stability (Martin), facades, strongly connected components (Tarjan),
transitive reduction (Aho, Garey & Ullman), upward dependencies by layer, NCCD (Lakos), modularity (Newman),
propagation cost (MacCormack). `measure` returns them all for one (nodes, edges) pair."""
import sys
from collections import defaultdict
from pathlib import Path

from codefiles import HUB_FAN


# ---- metrics ------------------------------------------------------------------------------------------------

STABLE_MAX = 0.25          # Martin's instability I = out / (in + out); at or below this a node is stable
FACADE_NAMES = {"__init__.py", "index.ts", "index.tsx", "index.js", "mod.rs"}
ROOT_STEMS = {"composition", "main", "app", "index", "server", "wiring"}
LAYER = {  # folder name -> level; an edge from a lower level to a higher one is an upward dependency
    "controllers": 4, "routers": 4, "views": 4, "pages": 4, "api": 4, "features": 4,
    "services": 3, "use_cases": 3, "usecases": 3, "application": 3,
    "adapters": 2, "repositories": 2, "ports": 2, "infrastructure": 2,
    "models": 1, "domain": 1, "schemas": 1, "types": 1, "core": 1, "shared": 1, "errors": 1,
}


def is_root_or_test(node: str) -> bool:
    """Composition roots and tests wire or exercise many modules directly: their out-edges are wiring, not design."""
    p = Path(node)
    return (p.stem.lower() in ROOT_STEMS and p.name not in FACADE_NAMES) or "tests" in p.parts or "test" in p.parts \
        or p.name.startswith("test_") or ".test." in p.name or ".spec." in p.name or p.name.endswith("_test.py")


def is_composition_root(node: str) -> bool:
    p = Path(node)
    return p.stem in ROOT_STEMS and p.name not in FACADE_NAMES


def layer_of(node: str):
    levels = [LAYER[part] for part in Path(node).parts if part in LAYER]
    return levels[-1] if levels else None


def _is_facade(n: str, targets: set) -> bool:
    """A re-export file whose dependencies all lie inside its own folder."""
    folder = Path(n).parent
    return Path(n).name in FACADE_NAMES and bool(targets) and all(Path(b).parent == folder or folder in Path(b).parents for b in targets)


def _redirect(edges, out: dict, facades: set) -> set:
    new_edges = set()
    for a, b in edges:
        if a in facades:
            continue
        new_edges |= {(a, x) for x in (out[b] if b in facades else {b}) if x != a}
    return new_edges


def collapse_facades(nodes, edges):
    """A facade (__init__.py / index.ts / mod.rs) whose dependencies all lie inside its own folder is a name for
    its submodules, not a module. Edges into it are redirected to what it re-exports; the facade is dropped."""
    out = defaultdict(set)
    for a, b in edges:
        out[a].add(b)
    facades = {n for n in nodes if _is_facade(n, out[n])}
    for _ in range(10):  # facades re-exporting facades
        for f in facades:
            out[f] = {x for b in out[f] for x in (out[b] if b in facades and b != f else {b})}
    return nodes - facades, _redirect(edges, out, facades), len(facades)


def components(nodes, edges):
    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in edges:
        parent[find(a)] = find(b)
    return len({find(n) for n in nodes})


class _Tarjan:
    """Tarjan's strongly connected components; `components` holds those with more than one node."""
    def __init__(self, adj):
        self.adj, self.index, self.low, self.stack, self.on, self.components, self.counter = adj, {}, {}, [], set(), [], 0

    def visit(self, v):
        self.index[v] = self.low[v] = self.counter; self.counter += 1
        self.stack.append(v); self.on.add(v)
        for w in self.adj[v]:
            if w not in self.index:
                self.visit(w); self.low[v] = min(self.low[v], self.low[w])
            elif w in self.on:
                self.low[v] = min(self.low[v], self.index[w])
        if self.low[v] == self.index[v]:
            self._pop_component(v)

    def _pop_component(self, v):
        comp = []
        while True:
            w = self.stack.pop(); self.on.discard(w); comp.append(w)
            if w == v:
                break
        if len(comp) > 1:
            self.components.append(sorted(comp))


def sccs(nodes, edges):
    """Tarjan; cycles = strongly connected components with more than one node."""
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
    sys.setrecursionlimit(max(10000, len(nodes) * 2))
    t = _Tarjan(adj)
    for v in sorted(nodes):
        if v not in t.index:
            t.visit(v)
    return t.components


def reach_sets(nodes, edges):
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
    reach = {}
    for n in nodes:
        seen, todo = set(), [n]
        while todo:
            x = todo.pop()
            for y in adj[x]:
                if y not in seen:
                    seen.add(y); todo.append(y)
        reach[n] = seen
    return adj, reach


def degrees(nodes, edges):
    fi, fo = defaultdict(int), defaultdict(int)
    for a, b in edges:
        fo[a] += 1; fi[b] += 1
    return fi, fo


def stable_nodes(nodes, edges):
    """Instability I = out / (in + out) (Martin 1994). I <= STABLE_MAX: stable; depending on it is free reuse."""
    fi, fo = degrees(nodes, edges)
    return {n for n in nodes if (fi[n] + fo[n]) == 0 or fo[n] / (fi[n] + fo[n]) <= STABLE_MAX}


def _contract_cycles(nodes, edges):
    """(rep, cycle_edges, cycle_minimum): each cycle contracted to one node; cycle_minimum = sum(k-1) over cycles."""
    scc_of = {n: i for i, comp in enumerate(sccs(nodes, edges)) for n in comp}
    rep = lambda n: f"<cycle {scc_of[n]}>" if n in scc_of else n
    cycle_edges = {(a, b) for a, b in edges if a in scc_of and scc_of.get(b) == scc_of[a]}
    sizes = defaultdict(int)
    for n in scc_of:
        sizes[scc_of[n]] += 1
    return rep, cycle_edges, sum(k - 1 for k in sizes.values())


def transitive_reduction(nodes, edges):
    """On the graph with each cycle contracted to one node: an edge A->C is redundant when C is reachable from A
    through another successor B (Aho, Garey & Ullman 1972; unique on a DAG). Returns (redundant {A->C: B}, cycle_edges,
    cycle_minimum) where cycle_minimum = sum(k-1) over cycles, the edges an acyclic version of each cycle needs."""
    rep, cycle_edges, cycle_min = _contract_cycles(nodes, edges)
    cnodes = {rep(n) for n in nodes}
    cedges = {(rep(a), rep(b)) for a, b in edges - cycle_edges}
    adj, reach = reach_sets(cnodes, cedges)
    redundant = {}
    for a, b in sorted(edges - cycle_edges):
        ra, rb = rep(a), rep(b)
        via = next((w for w in sorted(adj[ra]) if w != rb and rb in reach[w]), None)
        if via is not None:
            redundant[(a, b)] = via
    return redundant, cycle_edges, cycle_min


def upward_edges(nodes, edges):
    """Dependencies that point the wrong way regardless of reachability: into a composition root, or from a
    lower layer into a higher one (controllers > services > adapters/ports > models)."""
    out = []
    for a, b in sorted(edges):
        if is_root_or_test(a):
            continue
        if is_composition_root(b):
            out.append((a, b, "into the composition root"))
            continue
        la, lb = layer_of(a), layer_of(b)
        if la is not None and lb is not None and la < lb:
            out.append((a, b, f"layer {la} -> layer {lb}"))
    return out


def nccd(nodes, edges):
    """Lakos: CCD = sum over nodes of (1 + transitive dependencies); NCCD = CCD / CCD of a balanced binary tree of
    the same size, (N+1)·log2(N+1) − N. 1.0 = as coupled as an ideal tree; > 1 more coupled."""
    import math
    n = len(nodes)
    if n < 2:
        return 0.0
    _, reach = reach_sets(nodes, edges)
    ccd = sum(1 + len(reach[x]) for x in nodes)
    tree = (n + 1) * math.log2(n + 1) - n
    return ccd / tree


def modularity_q(nodes, edges, depth):
    """Newman–Girvan Q for the partition 'first `depth` path components'; edges taken undirected.
    Q = 1/2m · Σ (A_ij − k_i k_j / 2m) δ(c_i, c_j). ~0: folders mean nothing; 0.3–0.7: real community structure."""
    und = {tuple(sorted(e)) for e in edges if e[0] != e[1]}
    m = len(und)
    if m == 0:
        return 0.0, 0
    cluster = {n: "/".join(Path(n).parts[:depth]) for n in nodes}
    deg = defaultdict(int)
    for a, b in und:
        deg[a] += 1; deg[b] += 1
    inside = sum(1 for a, b in und if cluster[a] == cluster[b])
    deg_by_cluster = defaultdict(int)
    for n in nodes:
        deg_by_cluster[cluster[n]] += deg[n]
    expected = sum(d * d for d in deg_by_cluster.values()) / (4 * m * m)
    return inside / m - expected, len(set(cluster.values()))


def _complexity(nodes, edges, stable):
    """The counted edges (into non-stable nodes), the shortcuts among them, and the reducible cycle edges."""
    redundant, cycle_edges, cycle_min = transitive_reduction(nodes, edges)
    counted = {(a, b) for a, b in edges if b not in stable}                   # complexity: edges into non-stable nodes
    wiring = {(a, b) for a, b in counted if is_root_or_test(a)}                # roots/tests: wiring, never shortcuts
    shortcuts = {e: via for e, via in redundant.items() if e in counted and e not in wiring}
    cyc_reducible = max(0, len(cycle_edges & counted) - cycle_min)
    return counted, wiring, shortcuts, cyc_reducible


def measure(nodes, edges):
    nodes, edges, facades = collapse_facades(set(nodes), set(edges))
    stable = stable_nodes(nodes, edges)
    counted, wiring, shortcuts, cyc_reducible = _complexity(nodes, edges, stable)
    complexity = len(counted)
    ideal = complexity - len(shortcuts) - cyc_reducible
    fi, fo = degrees(nodes, edges)
    _, reach = reach_sets(nodes, edges)
    return dict(
        n=len(nodes), e=len(edges), p=components(nodes, edges), facades=facades,
        stable=len(stable), reuse=len(edges) - complexity, wiring=len(wiring),
        complexity=complexity, ideal=ideal, shortcuts=shortcuts, cyc_reducible=cyc_reducible,
        reducible=(complexity - ideal), reducible_pct=((complexity - ideal) / ideal * 100 if ideal else 0.0),
        cycles=sccs(nodes, edges), upward=upward_edges(nodes, edges),
        hubs=sorted((x for x in nodes if fi[x] >= HUB_FAN and fo[x] >= HUB_FAN), key=lambda x: -(fi[x] + fo[x])),
        fi=fi, fo=fo,
        prop=(sum(len(r) for r in reach.values()) / (len(nodes) ** 2) * 100 if nodes else 0.0),
        nccd=nccd(nodes, edges),
        q={d: modularity_q(nodes, edges, d) for d in (1, 2, 3)},
    )
