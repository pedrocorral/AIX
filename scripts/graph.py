#!/usr/bin/env python3
"""aix graph — measure the codebase dependency graph: complexity vs ideal complexity.

Nodes are modules (files) for Python, JavaScript/TypeScript, Rust and Java, or functions/methods for Python
(`--functions`). Edges are imports / calls between project files (external packages ignored).

  complexity        edges of the inner graph (leaves excluded: edges INTO a pure leaf are free reuse)
  ideal complexity  edges of its transitive reduction (Aho, Garey & Ullman 1972): every dependency path kept,
                    shortcuts and cycles removed. The lowest complexity with the same dependencies.
  reducible         (complexity - ideal) / ideal, as %: what could be removed without losing any dependency path.
                    0 % = nothing to reduce. Shortcuts are layer skips (A->C while A->B->C); cycle edges are defects.
  shape             circuit rank E - N + P (Berge) and its % above a forest: how diamond-rich the DAG is. Diamonds
                    are two genuine paths to one node and are NOT reducible; reported for the trend only.
  cycles            strongly connected components with more than one node: the defects
  hubs           nodes with high fan-in AND high fan-out: changes there propagate everywhere
  propagation    average share of the graph reachable from a node (MacCormack, Rusnak & Baldwin 2006)

Static analysis is approximate for dynamic languages: unresolved imports/calls are ignored, never guessed."""
import ast, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE_ROOTS = ["backend", "frontend", "shared", "infra", "src", "app", "tests", "lib"]
SKIP = {"node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".git", "target", ".next"}
EXT = {".py": "python", ".js": "js", ".jsx": "js", ".ts": "js", ".tsx": "js", ".mjs": "js", ".rs": "rust", ".java": "java"}
HUB_FAN = 3


# ---- file discovery -------------------------------------------------------------------------------------

def source_files(roots):
    for root in roots:
        base = (ROOT / root) if not Path(root).is_absolute() else Path(root)
        if not base.exists():
            continue
        files = [base] if base.is_file() else base.rglob("*")
        for f in files:
            if f.is_file() and f.suffix in EXT and not any(s in f.parts for s in SKIP) and f.stat().st_size > 0:
                yield f  # empty files (bare __init__.py) are not nodes


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


# ---- module-level edges per language ----------------------------------------------------------------------

PY_PROJECT_MARKERS = ("pyproject.toml", "setup.py", "setup.cfg", "requirements.txt")


def import_roots(f: Path):
    """Directories absolute imports resolve against, like sys.path: the project root, each code root, every
    directory holding a Python project marker, and their `src/`. Deliberately NOT "nearest non-package ancestor":
    namespace packages (no __init__.py) would turn `.../adapters/git/` into a top-level `git` and shadow GitPython."""
    roots = {ROOT} | {ROOT / r for r in CODE_ROOTS if (ROOT / r).is_dir()}
    if not (f.resolve().parent / "__init__.py").exists():
        roots.add(f.resolve().parent)  # a script directory: Python puts it on sys.path, siblings import by bare name
    for d in [f.resolve().parent, *f.resolve().parents]:
        if any((d / m).exists() for m in PY_PROJECT_MARKERS):
            roots.add(d)
            if (d / "src").is_dir():
                roots.add(d / "src")
        if d == ROOT:
            break
    return roots


def python_index(files):
    """dotted name -> file, keyed exactly as an absolute import would name it from one of the import roots."""
    idx = {}
    for f in files:
        if f.suffix != ".py":
            continue
        for root in import_roots(f):
            try:
                parts = list(f.resolve().relative_to(root).with_suffix("").parts)
            except ValueError:
                continue
            if parts[-1] == "__init__":
                parts = parts[:-1]
            if parts:
                idx.setdefault(".".join(parts), f)
    return idx


def resolve_py(name: str, idx):
    parts = name.split(".")
    while parts:
        if ".".join(parts) in idx:
            return idx[".".join(parts)]
        parts.pop()
    return None


def py_module_edges(f: Path, idx):
    try:
        tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    pkg = list(f.resolve().relative_to(ROOT).parent.parts)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [resolve_py(a.name, idx) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = ".".join(pkg[: len(pkg) - (node.level - 1)]) if node.level else ""
            mod = ".".join(x for x in (base, node.module or "") if x)
            hits = [resolve_py(f"{mod}.{a.name}" if mod else a.name, idx) for a in node.names]
            out += [h for h in hits if h] or [resolve_py(mod, idx)]
    return [t for t in out if t and t.resolve() != f.resolve()]


JS_IMPORT = re.compile(r"""(?:import|export)\s[^'"]*?from\s*['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\)|import\(\s*['"]([^'"]+)['"]\s*\)""")


def js_module_edges(f: Path):
    out = []
    for m in JS_IMPORT.finditer(f.read_text(encoding="utf-8", errors="replace")):
        spec = next(g for g in m.groups() if g)
        if not spec.startswith("."):
            continue
        base = (f.parent / spec)
        cands = [base] + [base.with_suffix(e) for e in (".ts", ".tsx", ".js", ".jsx", ".mjs")] + [base / f"index{e}" for e in (".ts", ".tsx", ".js", ".jsx")]
        hit = next((c for c in cands if c.is_file()), None)
        if hit:
            out.append(hit)
    return out


RS_USE = re.compile(r"^\s*(?:pub\s+)?(?:use|mod)\s+([A-Za-z_:][\w:]*)", re.M)


def rust_module_edges(f: Path):
    out, text = [], f.read_text(encoding="utf-8", errors="replace")
    crate_root = next((p for p in f.parents if (p / "Cargo.toml").exists()), f.parent) / "src"
    for m in RS_USE.finditer(text):
        path = m.group(1).split("::")
        if path[0] == "crate":
            base, path = crate_root, path[1:]
        elif path[0] == "super":
            base, path = f.parent.parent, path[1:]
        elif path[0] == "self":
            base, path = f.parent, path[1:]
        elif m.group(0).lstrip().startswith(("mod", "pub mod")):
            base = f.parent if f.name in ("mod.rs", "lib.rs", "main.rs") else f.with_suffix("")
        else:
            continue
        for n in range(len(path), 0, -1):
            cand = base.joinpath(*path[:n])
            hit = next((c for c in (cand.with_suffix(".rs"), cand / "mod.rs") if c.is_file()), None)
            if hit:
                out.append(hit); break
    return out


JAVA_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)\s*;", re.M)


def java_module_edges(f: Path, java_idx):
    out = []
    for m in JAVA_IMPORT.finditer(f.read_text(encoding="utf-8", errors="replace")):
        parts = m.group(1).split(".")
        for n in range(len(parts), 0, -1):
            hit = java_idx.get("/".join(parts[:n]))
            if hit:
                out.append(hit); break
    return out


def module_graph(roots):
    files = list(source_files(roots))
    py_idx = python_index(files)
    java_idx = {}
    for f in files:
        if f.suffix == ".java":
            parts = f.resolve().relative_to(ROOT).with_suffix("").parts
            for i in range(len(parts)):
                java_idx.setdefault("/".join(parts[i:]), f)
    edges = set()
    for f in files:
        lang = EXT[f.suffix]
        targets = (py_module_edges(f, py_idx) if lang == "python" else js_module_edges(f) if lang == "js"
                   else rust_module_edges(f) if lang == "rust" else java_module_edges(f, java_idx))
        for t in targets:
            if t.resolve() != f.resolve():
                edges.add((rel(f), rel(t)))
    return {rel(f) for f in files}, edges


# ---- function-level graph (Python) -----------------------------------------------------------------------

def function_graph(roots):
    """Nodes `file:Class.method` / `file:func`; edges from calls resolved by name within the module, via
    imported names, and `self.method()` inside a class."""
    files = [f for f in source_files(roots) if f.suffix == ".py"]
    py_idx = python_index(files)
    defs, nodes = {}, set()          # (file, simple name) -> qualified node
    trees = {}
    for f in files:
        try:
            trees[f] = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for cls, fn in iter_functions(trees[f]):
            q = f"{rel(f)}:{cls + '.' if cls else ''}{fn.name}"
            nodes.add(q); defs[(rel(f), fn.name)] = q
            if cls:
                defs[(rel(f), f"{cls}.{fn.name}")] = q
    edges = set()
    for f, tree in trees.items():
        imported = imported_names(tree, f, py_idx)
        for cls, fn in iter_functions(tree):
            src = defs[(rel(f), fn.name)] if not cls else defs[(rel(f), f"{cls}.{fn.name}")]
            for call in (n for n in ast.walk(fn) if isinstance(n, ast.Call)):
                tgt = resolve_call(call.func, rel(f), cls, imported, defs)
                if tgt and tgt != src:
                    edges.add((src, tgt))
    return nodes, edges


def iter_functions(tree):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield None, node
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    yield node.name, sub


def imported_names(tree, f, py_idx):
    """local name -> (file, original name) for `from m import x` and `import m [as n]`."""
    out = {}
    pkg = list(f.resolve().relative_to(ROOT).parent.parts)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            base = ".".join(pkg[: len(pkg) - (node.level - 1)]) if node.level else ""
            mod = ".".join(x for x in (base, node.module or "") if x)
            target = resolve_py(mod, py_idx)
            if target:
                for a in node.names:
                    out[a.asname or a.name] = (rel(target), a.name)
        elif isinstance(node, ast.Import):
            for a in node.names:
                target = resolve_py(a.name, py_idx)
                if target:
                    out[a.asname or a.name.split(".")[-1]] = (rel(target), None)
    return out


def resolve_call(func, file, cls, imported, defs):
    if isinstance(func, ast.Name):
        if func.id in imported and imported[func.id][1]:
            return defs.get(imported[func.id])
        return defs.get((file, func.id))
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            if func.value.id == "self" and cls:
                return defs.get((file, f"{cls}.{func.attr}"))
            if func.value.id in imported and imported[func.value.id][1] is None:
                return defs.get((imported[func.value.id][0], func.attr))
            return defs.get((file, f"{func.value.id}.{func.attr}"))
    return None


# ---- metrics ------------------------------------------------------------------------------------------------

def components(nodes, edges):
    parent = {n: n for n in nodes}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in edges:
        parent[find(a)] = find(b)
    return len({find(n) for n in nodes})


def sccs(nodes, edges):
    """Tarjan; returns cycles (SCCs with >1 node)."""
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
    index, low, stack, on, out, counter = {}, {}, [], set(), [], [0]

    def strong(v):
        index[v] = low[v] = counter[0]; counter[0] += 1
        stack.append(v); on.add(v)
        for w in adj[v]:
            if w not in index:
                strong(w); low[v] = min(low[v], low[w])
            elif w in on:
                low[v] = min(low[v], index[w])
        if low[v] == index[v]:
            comp = []
            while True:
                w = stack.pop(); on.discard(w); comp.append(w)
                if w == v:
                    break
            if len(comp) > 1:
                out.append(sorted(comp))
    sys.setrecursionlimit(max(10000, len(nodes) * 2))
    for v in nodes:
        if v not in index:
            strong(v)
    return out


def propagation_cost(nodes, edges):
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b)
    total = 0
    for n in nodes:
        seen, todo = set(), [n]
        while todo:
            x = todo.pop()
            for y in adj[x]:
                if y not in seen:
                    seen.add(y); todo.append(y)
        total += len(seen)
    return total / (len(nodes) ** 2) * 100 if nodes else 0.0


def excess(nodes, edges):
    n, e, p = len(nodes), len(edges), components(nodes, edges)
    ground = n - p
    rank = e - ground
    return ground, rank, (rank / ground * 100 if ground else 0.0)


def leaf_adjusted(nodes, edges):
    fan_out = defaultdict(int)
    for a, _ in edges:
        fan_out[a] += 1
    inner = {n for n in nodes if fan_out[n] > 0}
    inner_edges = {(a, b) for a, b in edges if b in inner}
    return inner, inner_edges, excess(inner, inner_edges)


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


def ideal_complexity(nodes, edges):
    """Edges of the transitive reduction (Aho, Garey & Ullman 1972): the smallest graph with the same reachability.
    Every dependency path is kept; only shortcuts go (A->C when A already reaches C through B). Cycles have no
    reduction, so each strongly connected component of k nodes is counted at its acyclic minimum, k-1 edges, and
    the rest of its internal edges are reducible. Edges out of a composition root or a test are wiring, never shortcuts.
    Returns (ideal_edge_count, shortcut_edges, reducible_cycle_edge_count)."""
    scc_of = {}
    for i, comp in enumerate(sccs(nodes, edges)):
        for n in comp:
            scc_of[n] = i
    cycle_edges = {(a, b) for a, b in edges if a in scc_of and scc_of.get(b) == scc_of[a]}
    dag = edges - cycle_edges
    adj, reach = reach_sets(nodes, dag)
    shortcuts = {(a, b) for a, b in dag if not is_composition_root(a) and any(b in reach[w] for w in adj[a] if w != b)}
    sizes = defaultdict(int)
    for n in scc_of:
        sizes[scc_of[n]] += 1
    cycle_min = sum(k - 1 for k in sizes.values())
    ideal = len(dag) - len(shortcuts) + cycle_min
    return ideal, shortcuts, len(cycle_edges) - cycle_min


FACADE_NAMES = {"__init__.py", "index.ts", "index.tsx", "index.js", "mod.rs"}
ROOT_STEMS = {"composition", "main", "app", "index", "server", "wiring"}


def is_composition_root(node: str) -> bool:
    """Composition roots and tests wire or exercise many modules directly: their out-edges are never shortcuts."""
    p = Path(node)
    return (p.stem in ROOT_STEMS and p.name not in FACADE_NAMES) or "tests" in p.parts or "test" in p.parts \
        or p.name.startswith("test_") or ".test." in p.name or ".spec." in p.name or p.name.endswith("_test.py")


def collapse_facades(nodes, edges):
    """A facade is an __init__.py / index.ts / mod.rs whose dependencies all lie inside its own folder: a name for
    its submodules, not a module. Edges into a facade are redirected to what it re-exports and the facade is
    dropped, so `router -> models/__init__ -> user` plus `router -> user` is one dependency, not a shortcut."""
    out = defaultdict(set)
    for a, b in edges:
        out[a].add(b)
    facades = {n for n in nodes if Path(n).name in FACADE_NAMES and out[n]
               and all(Path(b).parent == Path(n).parent or Path(n).parent in Path(b).parents for b in out[n])}
    changed = True
    while changed:  # facades re-exporting facades
        changed = False
        for f in list(facades):
            if any(b in facades for b in out[f]):
                out[f] = {x for b in out[f] for x in (out[b] if b in facades else {b})}
                changed = True if any(b in facades for b in out[f]) else changed
    new_edges = set()
    for a, b in edges:
        if a in facades:
            continue
        targets = out[b] if b in facades else {b}
        new_edges |= {(a, x) for x in targets if x != a}
    return nodes - facades, new_edges, len(facades)


def degrees(nodes, edges):
    fi, fo = defaultdict(int), defaultdict(int)
    for a, b in edges:
        fo[a] += 1; fi[b] += 1
    return fi, fo


# ---- report -----------------------------------------------------------------------------------------------

def measure(nodes, edges):
    ground, rank, pct = excess(nodes, edges)
    nodes, edges, facades = collapse_facades(nodes, edges)
    inner, inner_edges, (g2, r2, pct2) = leaf_adjusted(nodes, edges)
    ideal, shortcuts, cycle_edges = ideal_complexity(inner, inner_edges)
    reducible = len(inner_edges) - ideal
    fi, fo = degrees(nodes, edges)
    return dict(n=len(nodes), e=len(edges), p=components(nodes, edges), ground=ground, rank=rank, pct=pct,
                inner=len(inner), inner_edges=len(inner_edges), ground2=g2, rank2=r2, pct2=pct2,
                ideal=ideal, reducible=reducible, reducible_pct=(reducible / ideal * 100 if ideal else 0.0),
                shortcuts=sorted(shortcuts), cycle_edges=cycle_edges, facades=facades,
                cycles=sccs(nodes, edges), hubs=sorted((n for n in nodes if fi[n] >= HUB_FAN and fo[n] >= HUB_FAN), key=lambda n: -(fi[n] + fo[n])),
                fan_out=sorted(nodes, key=lambda n: -fo[n])[:5], fi=fi, fo=fo, prop=propagation_cost(nodes, edges))


def render(m, level, scope):
    lines = [f"Dependency graph ({level}) — {scope}", "",
             f"  nodes {m['n']}, edges {m['e']}, components {m['p']}; {m['facades']} facades (__init__/index re-exports) collapsed;",
             f"  inner graph (leaves excluded, their reuse is free): {m['inner']} nodes, {m['inner_edges']} edges",
             f"  complexity        {m['inner_edges']} edges",
             f"  ideal complexity  {m['ideal']} edges  (transitive reduction: every dependency path kept, shortcuts and cycles removed)",
             f"  reducible         {m['reducible_pct']:.1f} %  ({m['reducible']} edges add no dependency path: {len(m['shortcuts'])} shortcuts, {m['cycle_edges']} cycle edges)",
             f"  propagation cost  {m['prop']:.1f} %  (average share of the graph a change can reach)",
             f"  shape: circuit rank {m['rank']} = {m['pct']:.1f} % above a forest (diamonds; not reducible by itself), leaf-adjusted {m['pct2']:.1f} %",
             f"  cycles {len(m['cycles'])}, hubs {len(m['hubs'])} (fan-in and fan-out both >= {HUB_FAN})", ""]
    for c in m["cycles"][:10]:
        lines.append(f"  CYCLE     {' -> '.join(c)} -> {c[0]}")
    for a, b in m["shortcuts"][:10]:
        lines.append(f"  SHORTCUT  {a} -> {b}  (already reached through an intermediate: a layer skip)")
    for h in m["hubs"][:10]:
        note = "composition root / entry point: a hub by design" if Path(h).stem in ("composition", "main", "app", "index", "server", "wiring") else "split it: keep the leaf part, move the rest up"
        lines.append(f"  HUB       {h}  (in {m['fi'][h]}, out {m['fo'][h]})  {note}")
    if m["fan_out"] and m["fo"][m["fan_out"][0]] > 0:
        lines.append("  top fan-out: " + ", ".join(f"{n} ({m['fo'][n]})" for n in m["fan_out"] if m["fo"][n] > 0))
    return "\n".join(lines)


def write_report(text: str):
    out = ROOT / "docs" / "tests" / "dependency-graph.md"
    out.write_text("# Dependency graph (generated — do not edit)\n\n```\n" + text + "\n```\n", encoding="utf-8")
    return out


USAGE = "usage: aix graph [PATH...] [--functions] [--gate] [--max-reducible PCT] [--report]"


def main(args):
    functions, gate, report = "--functions" in args, "--gate" in args, "--report" in args
    max_reducible = None
    for flag in ("--max-reducible", "--max-excess"):  # --max-excess kept as an alias
        if flag in args:
            i = args.index(flag); max_reducible = float(args[i + 1]); del args[i:i + 2]
    paths = [a for a in args if not a.startswith("--")] or CODE_ROOTS
    nodes, edges = function_graph(paths) if functions else module_graph(paths)
    if not nodes:
        sys.exit(f"no source files under {', '.join(paths)} (looked for {', '.join(EXT)})")
    m = measure(nodes, edges)
    text = render(m, "functions" if functions else "modules", ", ".join(paths))
    print(text)
    if report:
        print(f"\n  wrote {write_report(text).relative_to(ROOT)}")
    if gate:
        bad = []
        if m["cycles"]:
            bad.append(f"{len(m['cycles'])} cycle(s)")
        if max_reducible is not None and m["reducible_pct"] > max_reducible:
            bad.append(f"reducible complexity {m['reducible_pct']:.1f} % > {max_reducible:g} %")
        if bad:
            sys.exit("GATE FAILED: " + "; ".join(bad))
        print("GATE PASSED")


if __name__ == "__main__":
    main(sys.argv[1:])
