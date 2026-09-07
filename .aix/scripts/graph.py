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
import ast, re, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE_ROOTS = ["backend", "frontend", "shared", "infra", "src", "app", "tests", "lib"]
SKIP = {"node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".git", "target", ".next", ".aix"}
EXT = {".py": "python", ".js": "js", ".jsx": "js", ".ts": "js", ".tsx": "js", ".mjs": "js", ".rs": "rust", ".java": "java"}
HUB_FAN = 3


# ---- file discovery -------------------------------------------------------------------------------------

def source_files(roots):
    for root in roots:
        base = (ROOT / root) if not Path(root).is_absolute() else Path(root)
        if not base.exists():
            continue
        files = [base] if base.is_file() else base.rglob("*")
        for f in files:  # SKIP applies below the given base only: an explicit `.aix/scripts` target is measured
            inner = f.relative_to(base).parts if base.is_dir() else ()
            if f.is_file() and f.suffix in EXT and not any(s in inner for s in SKIP) and f.stat().st_size > 0:
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
    return (p.stem in ROOT_STEMS and p.name not in FACADE_NAMES) or "tests" in p.parts or "test" in p.parts \
        or p.name.startswith("test_") or ".test." in p.name or ".spec." in p.name or p.name.endswith("_test.py")


def is_composition_root(node: str) -> bool:
    p = Path(node)
    return p.stem in ROOT_STEMS and p.name not in FACADE_NAMES


def layer_of(node: str):
    levels = [LAYER[part] for part in Path(node).parts if part in LAYER]
    return levels[-1] if levels else None


def collapse_facades(nodes, edges):
    """A facade (__init__.py / index.ts / mod.rs) whose dependencies all lie inside its own folder is a name for
    its submodules, not a module. Edges into it are redirected to what it re-exports; the facade is dropped."""
    out = defaultdict(set)
    for a, b in edges:
        out[a].add(b)
    facades = {n for n in nodes if Path(n).name in FACADE_NAMES and out[n]
               and all(Path(b).parent == Path(n).parent or Path(n).parent in Path(b).parents for b in out[n])}
    for _ in range(10):  # facades re-exporting facades
        for f in facades:
            out[f] = {x for b in out[f] for x in (out[b] if b in facades and b != f else {b})}
    new_edges = set()
    for a, b in edges:
        if a in facades:
            continue
        for x in (out[b] if b in facades else {b}):
            if x != a:
                new_edges.add((a, x))
    return nodes - facades, new_edges, len(facades)


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
    """Tarjan; cycles = strongly connected components with more than one node."""
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
    for v in sorted(nodes):
        if v not in index:
            strong(v)
    return out


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


def transitive_reduction(nodes, edges):
    """On the graph with each cycle contracted to one node: an edge A->C is redundant when C is reachable from A
    through another successor B (Aho, Garey & Ullman 1972; unique on a DAG). Returns (redundant {A->C: B}, cycle_edges,
    cycle_minimum) where cycle_minimum = sum(k-1) over cycles, the edges an acyclic version of each cycle needs."""
    scc_of = {}
    for i, comp in enumerate(sccs(nodes, edges)):
        for n in comp:
            scc_of[n] = i
    rep = lambda n: f"<cycle {scc_of[n]}>" if n in scc_of else n
    cycle_edges = {(a, b) for a, b in edges if a in scc_of and scc_of.get(b) == scc_of[a]}
    cnodes = {rep(n) for n in nodes}
    cedges = {(rep(a), rep(b)) for a, b in edges - cycle_edges}
    adj, reach = reach_sets(cnodes, cedges)
    redundant = {}
    for a, b in sorted(edges - cycle_edges):
        ra, rb = rep(a), rep(b)
        via = next((w for w in sorted(adj[ra]) if w != rb and rb in reach[w]), None)
        if via is not None:
            redundant[(a, b)] = via
    sizes = defaultdict(int)
    for n in scc_of:
        sizes[scc_of[n]] += 1
    return redundant, cycle_edges, sum(k - 1 for k in sizes.values())


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


def measure(nodes, edges):
    nodes, edges, facades = collapse_facades(set(nodes), set(edges))
    stable = stable_nodes(nodes, edges)
    redundant, cycle_edges, cycle_min = transitive_reduction(nodes, edges)
    counted = {(a, b) for a, b in edges if b not in stable}                   # complexity: edges into non-stable nodes
    wiring = {(a, b) for a, b in counted if is_root_or_test(a)}                # roots/tests: wiring, never shortcuts
    shortcuts = {e: via for e, via in redundant.items() if e in counted and e not in wiring}
    cyc_counted = {e for e in cycle_edges if e in counted}
    cyc_reducible = max(0, len(cyc_counted) - cycle_min)
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


# ---- dead code --------------------------------------------------------------------------------------------------

ENTRY_STEMS = ROOT_STEMS | {"manage", "wsgi", "asgi", "cli", "conftest", "setup", "settings", "config"}
ENTRY_SUFFIX = (".config.ts", ".config.js", ".config.mjs", ".d.ts")


def has_main_guard(node: str) -> bool:
    """A Python file run as a script (`if __name__ == "__main__":`) is an entry point in its own right."""
    f = ROOT / node
    return f.suffix == ".py" and f.is_file() and '__name__ == "__main__"' in f.read_text(encoding="utf-8", errors="replace")


def is_entry_module(node: str) -> bool:
    """Modules nothing needs to import for them to be alive: entry points, tests, framework/tool config, scripts."""
    p = Path(node)
    return is_root_or_test(node) or p.stem in ENTRY_STEMS or p.name.endswith(ENTRY_SUFFIX) or p.name in FACADE_NAMES \
        or has_main_guard(node)


def dead_modules(nodes, edges):
    """Files no entry module reaches through imports. Reachability, not fan-in: an orphan cluster that imports
    each other is dead as a whole."""
    roots = {n for n in nodes if is_entry_module(n)}
    _, reach = reach_sets(nodes, edges)
    live = set(roots) | {x for r in roots for x in reach[r]}
    return roots, sorted(n for n in nodes if n not in live)


IMPLICIT_NAMES = {"main", "setup", "teardown", "setUp", "tearDown"}


def dead_functions(roots):
    """Python functions/methods whose simple name is never referenced anywhere (as a bare name or an attribute)
    outside their own definition, are not decorated (routes, fixtures, commands are called by the framework),
    are not dunder/implicit, not in __all__, and not in an entry/test file. Same rule as vulture: name-based,
    so a method called through any object of the same name counts as live. Conservative by design."""
    files = [f for f in source_files(roots) if f.suffix == ".py"]
    trees = {}
    for f in files:
        try:
            trees[f] = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
    used, exported, defs = defaultdict(int), set(), []
    for f, tree in trees.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                used[node.id] += 1
            elif isinstance(node, ast.Attribute):
                used[node.attr] += 1
            elif isinstance(node, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "__all__" for x in node.targets):
                exported |= {c.value for c in ast.walk(node.value) if isinstance(c, ast.Constant) and isinstance(c.value, str)}
        for cls, fn in iter_functions(tree):
            defs.append((rel(f), cls, fn))
    dead = []
    for file, cls, fn in defs:
        name = fn.name
        if is_entry_module(file) or fn.decorator_list or name in exported or name in IMPLICIT_NAMES \
                or (name.startswith("__") and name.endswith("__")) or name.startswith("test"):
            continue
        if used[name] == 0:  # a def is not an ast.Name, so any count is a real reference
            dead.append((f"{file}:{cls + '.' if cls else ''}{name}", fn.lineno))
    return sorted(dead)


def render_dead(nodes, edges, paths, functions):
    roots, dead = dead_modules(nodes, edges)
    lines = ["", f"Dead code — {', '.join(paths)}", "",
             f"  entry modules (live by definition): {len(roots)}  e.g. " + ", ".join(sorted(roots)[:6]),
             f"  DEAD MODULES {len(dead)}  (no entry module reaches them through imports)"]
    lines += [f"    {n}" for n in dead[:40]]
    if functions:
        df = dead_functions(paths)
        lines += [f"  DEAD FUNCTIONS {len(df)}  (Python: name never referenced outside its definition; decorated, dunder, exported and entry/test code excluded)"]
        lines += [f"    {q}  (line {ln})" for q, ln in df[:60]]
    else:
        lines.append("  (add --functions for Python dead functions and methods)")
    lines.append("  Every line is a candidate: confirm nothing reaches it by string, reflection or a framework before deleting. Fix with: skill refactor-dead")
    return "\n".join(lines), len(dead) + (len(df) if functions else 0)


# ---- clones -------------------------------------------------------------------------------------------------------

MIN_LINES, KGRAM, WINDOW, SIMILARITY = 6, 5, 4, 70
KEYWORDS = set("""if else for while do return break continue switch case default try catch finally throw new delete
typeof instanceof in of function class extends import export from const let var async await yield this super null
true false undefined void fn let mut pub struct enum impl trait match loop use mod ref self Some None Ok Err
public private protected static final abstract interface package void int long double float boolean char byte short
""".split())
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`[^`]*`|\d+(?:\.\d+)?|[A-Za-z_]\w*|[^\sA-Za-z_0-9]')
FUNC_HEAD = {
    # function f( | const f[: Type] = [async] (params[: Ret]) => { | method(params)[: Ret] {   (params may nest one level of parens)
    "js": re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\s*\*?\s*(\w+)\s*\(|(?:const|let|var)\s+(\w+)\s*(?::\s*[^=]+?)?=\s*(?:async\s*)?(?:\((?:[^()]|\([^()]*\))*\)|\w+)\s*(?::\s*[^=]+?)?=>\s*\{|(?:public|private|protected|static|async|\s)*(\w+)\s*\((?:[^()]|\([^()]*\))*\)\s*(?::\s*[^{]+)?\{)", re.M | re.S),
    "rust": re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+(\w+)", re.M),
    "java": re.compile(r"^\s*(?:public|private|protected|static|final|abstract|synchronized|\s)*[\w<>\[\], ]+\s+(\w+)\s*\([^)]*\)\s*(?:throws[^{]+)?\{", re.M),
}


def normalise_py(fn) -> list:
    """Structure tokens of a Python function: node kinds, with identifiers -> NAME/ATTR/ARG and literals -> their
    type, docstring dropped. Two functions with equal sequences are type-1/2 clones."""
    body = fn.body[1:] if fn.body and isinstance(fn.body[0], ast.Expr) and isinstance(getattr(fn.body[0], "value", None), ast.Constant) and isinstance(fn.body[0].value.value, str) else fn.body
    out = []

    def visit(node):
        if isinstance(node, ast.Name):
            out.append("NAME")
        elif isinstance(node, ast.Attribute):
            out.append("ATTR"); visit(node.value)
        elif isinstance(node, ast.arg):
            out.append("ARG")
        elif isinstance(node, ast.Constant):
            out.append(type(node.value).__name__.upper())
        else:
            out.append(type(node).__name__)
            for child in ast.iter_child_nodes(node):
                visit(child)
    for a in fn.args.args + fn.args.kwonlyargs:
        visit(a)
    for stmt in body:
        visit(stmt)
    return out


def normalise_tokens(text: str) -> list:
    """Token normalisation for JS/TS/Rust/Java bodies: identifiers -> ID, numbers -> NUM, strings -> STR, keywords and
    punctuation kept. Comments stripped first."""
    text = re.sub(r"//[^\n]*|/\*.*?\*/", " ", text, flags=re.S)
    out = []
    for tok in TOKEN.findall(text):
        if tok[0] in "\"'`":
            out.append("STR")
        elif tok[0].isdigit():
            out.append("NUM")
        elif tok[0].isalpha() or tok[0] == "_":
            out.append(tok if tok in KEYWORDS else "ID")
        else:
            out.append(tok)
    return out


def brace_block(text: str, start: int) -> str:
    """Text from the first '{' at/after `start` to its matching '}'."""
    i = text.find("{", start)
    if i < 0:
        return ""
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
    return text[i:]


def functions_for_clones(roots):
    """(node name, file, line, n_lines, token sequence) for every function big enough to matter."""
    out = []
    for f in source_files(roots):
        lang = EXT[f.suffix]
        text = f.read_text(encoding="utf-8", errors="replace")
        if lang == "python":
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue
            for cls, fn in iter_functions(tree):
                n_lines = (fn.end_lineno or fn.lineno) - fn.lineno + 1
                if n_lines >= MIN_LINES:
                    out.append((f"{rel(f)}:{cls + '.' if cls else ''}{fn.name}", rel(f), fn.lineno, n_lines, normalise_py(fn)))
        else:
            for m in FUNC_HEAD[lang].finditer(text):
                name = next((g for g in m.groups() if g), "anon")
                if name in KEYWORDS:
                    continue
                block = brace_block(text, m.end() - 1)
                n_lines = block.count("\n") + 1
                if n_lines >= MIN_LINES:
                    out.append((f"{rel(f)}:{name}", rel(f), text.count("\n", 0, m.start()) + 1, n_lines, normalise_tokens(block)))
    return out


def fingerprints(tokens) -> set:
    """Winnowing (Schleimer, Wilkerson & Aiken 2003): hash every k-gram, keep the minimum of each window."""
    if len(tokens) < KGRAM:
        return {hash(tuple(tokens))}
    grams = [hash(tuple(tokens[i:i + KGRAM])) for i in range(len(tokens) - KGRAM + 1)]
    if len(grams) <= WINDOW:
        return set(grams)
    return {min(grams[i:i + WINDOW]) for i in range(len(grams) - WINDOW + 1)}


def find_clones(funcs, similarity):
    """Exact groups (equal normalised sequences) and near pairs (Dice overlap of fingerprints >= similarity %)."""
    by_hash = defaultdict(list)
    for fx in funcs:
        by_hash[hash(tuple(fx[4]))].append(fx)
    exact = [g for g in by_hash.values() if len(g) > 1]
    in_exact = {fx[0] for g in exact for fx in g}
    prints = {fx[0]: fingerprints(fx[4]) for fx in funcs}
    index = defaultdict(set)
    for name, fp in prints.items():
        for h in fp:
            index[h].add(name)
    seen, near = set(), []
    info = {fx[0]: fx for fx in funcs}
    for name, fp in prints.items():
        candidates = {o for h in fp for o in index[h] if o != name}
        for other in candidates:
            pair = tuple(sorted((name, other)))
            if pair in seen or (name in in_exact and other in in_exact):
                continue
            seen.add(pair)
            a, b = prints[pair[0]], prints[pair[1]]
            dice = 2 * len(a & b) / (len(a) + len(b)) * 100
            if dice >= similarity:
                near.append((dice, info[pair[0]], info[pair[1]]))
    exact.sort(key=lambda g: -len(g) * g[0][3])
    near.sort(key=lambda x: -(x[0] * min(x[1][3], x[2][3])))
    return exact, near


def render_clones(roots, similarity):
    funcs = functions_for_clones(roots)
    exact, near = find_clones(funcs, similarity)
    lines = [f"Clones — {', '.join(roots)}", "",
             f"  functions analysed {len(funcs)} (>= {MIN_LINES} lines); exact clone groups {len(exact)} (types 1-2: same structure, names and literals may differ); near-clones {len(near)} (type 3: >= {similarity:g} % shared fingerprints, winnowing k={KGRAM})", ""]
    for g in exact[:20]:
        lines.append(f"  EXACT  {len(g)} × ~{g[0][3]} lines: " + ", ".join(f"{fx[0]} (l.{fx[2]})" for fx in g) + "   -> keep one, make it a leaf")
    for dice, a, b in near[:30]:
        lines.append(f"  NEAR   {dice:3.0f} %  {a[0]} (l.{a[2]}, {a[3]} lines)  ~  {b[0]} (l.{b[2]}, {b[3]} lines)   -> extract the shared part into a leaf")
    lines.append("  Every line is a candidate: two functions may legitimately share a shape (adapters of one port); merge only when they share a purpose. Fix with: skill refactor-clone")
    return "\n".join(lines), len(exact)


# ---- report -----------------------------------------------------------------------------------------------

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
    for c in m["cycles"][:10]:
        lines.append(f"  CYCLE     {' -> '.join(c)} -> {c[0]}")
    for a, b, why in m["upward"][:15]:
        lines.append(f"  UPWARD    {a} -> {b}  ({why})")
    for (a, b), via in sorted(m["shortcuts"].items())[:15]:
        lines.append(f"  SHORTCUT  {a} -> {b}  also reached via {via}")
    for h in m["hubs"][:10]:
        note = "composition root: a hub by design" if is_composition_root(h) else "split it: keep the stable part, move the rest up"
        lines.append(f"  HUB       {h}  (in {m['fi'][h]}, out {m['fo'][h]})  {note}")
    if m["cycles"] or m["upward"] or m["shortcuts"] or m["hubs"]:
        lines.append("  fix with: CYCLE/UPWARD -> skill refactor-cycle; SHORTCUT -> refactor-shortcut; HUB -> refactor-hub (aix skills show NAME)")
    return "\n".join(lines)


def write_report(text: str):
    out = ROOT / "docs" / "tests" / "dependency-graph.md"
    out.write_text("# Dependency graph (generated — do not edit)\n\n```\n" + text + "\n```\n", encoding="utf-8")
    return out


# ---- self-test: graphs with known answers -----------------------------------------------------------------------

def selftest():
    cases = [
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
    failed = 0
    for name, edges, want in cases:
        nodes = {n for e in edges for n in e}
        m = measure(nodes, edges)
        got = dict(reducible=m["reducible"], cycles=len(m["cycles"]), reuse=m["reuse"], upward=len(m["upward"]))
        ok = all(got[k] == v for k, v in want.items() if k != "shortcut") and ("shortcut" not in want or want["shortcut"] in m["shortcuts"])
        failed += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: {', '.join(f'{k}={got[k]}' for k in want if k != 'shortcut')}")
    print("selftest: " + ("all passed" if not failed else f"{failed} FAILED"))
    sys.exit(1 if failed else 0)


USAGE = "usage: aix code graph|dead|clones [PATH...] [--functions] [--similarity PCT] [--gate] [--max-reducible PCT] [--report] [--selftest]"


def main(args):
    if "--selftest" in args:
        return selftest()
    functions, gate, report, dead, clones = "--functions" in args, "--gate" in args, "--report" in args, "--dead" in args, "--clones" in args
    similarity = SIMILARITY
    if "--similarity" in args:
        i = args.index("--similarity"); similarity = float(args[i + 1]); del args[i:i + 2]
    max_reducible = None
    for flag in ("--max-reducible", "--max-excess"):  # --max-excess kept as an alias
        if flag in args:
            i = args.index(flag); max_reducible = float(args[i + 1]); del args[i:i + 2]
    paths = [a for a in args if not a.startswith("--")] or CODE_ROOTS
    nodes, edges = function_graph(paths) if functions else module_graph(paths)
    if not nodes:
        sys.exit(f"no source files under {', '.join(paths)} (looked for {', '.join(EXT)})")
    if clones:
        text, n_exact = render_clones(paths, similarity)
        print(text)
        if report:
            print(f"\n  wrote {write_report(text).relative_to(ROOT)}")
        if gate and n_exact:
            sys.exit(f"GATE FAILED: {n_exact} exact clone group(s)")
        if gate:
            print("GATE PASSED")
        return
    if dead:
        mnodes, medges = module_graph(paths)
        mn, me, _ = collapse_facades(set(mnodes), set(medges))
        text, n_dead = render_dead(mn, me, paths, functions)
        print(text.lstrip("\n"))
        if report:
            print(f"\n  wrote {write_report(text).relative_to(ROOT)}")
        if gate and n_dead:
            sys.exit(f"GATE FAILED: {n_dead} dead-code candidate(s)")
        if gate:
            print("GATE PASSED")
        return
    m = measure(nodes, edges)
    text = render(m, "functions" if functions else "modules", ", ".join(paths))
    print(text)
    if report:
        print(f"\n  wrote {write_report(text).relative_to(ROOT)}")
    if gate:
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


if __name__ == "__main__":
    main(sys.argv[1:])
