"""Leaf over codefiles: the edges of the dependency graph. Module-level imports per language (Python, JS/TS, Rust,
Java) resolved to project files, and Python call edges between functions. Unresolved imports are ignored, never
guessed."""
import ast, re
from pathlib import Path

from codefiles import ROOT, CODE_ROOTS, EXT, rel, source_files


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


def _from_import_targets(node, pkg: list, idx) -> list:
    base = ".".join(pkg[: len(pkg) - (node.level - 1)]) if node.level else ""
    mod = ".".join(x for x in (base, node.module or "") if x)
    hits = [resolve_py(f"{mod}.{a.name}" if mod else a.name, idx) for a in node.names]
    return [h for h in hits if h] or [resolve_py(mod, idx)]


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
            out += _from_import_targets(node, pkg, idx)
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


def _rust_base(m, f: Path, crate_root: Path):
    """(folder to resolve from, remaining path segments) for a `use`/`mod` line, or None when it is external."""
    path = m.group(1).split("::")
    if path[0] == "crate":
        return crate_root, path[1:]
    if path[0] == "super":
        return f.parent.parent, path[1:]
    if path[0] == "self":
        return f.parent, path[1:]
    if m.group(0).lstrip().startswith(("mod", "pub mod")):
        return (f.parent if f.name in ("mod.rs", "lib.rs", "main.rs") else f.with_suffix("")), path
    return None


def _rust_resolve(base: Path, path: list):
    for n in range(len(path), 0, -1):
        cand = base.joinpath(*path[:n])
        hit = next((c for c in (cand.with_suffix(".rs"), cand / "mod.rs") if c.is_file()), None)
        if hit:
            return hit
    return None


def rust_module_edges(f: Path):
    text = f.read_text(encoding="utf-8", errors="replace")
    crate_root = next((p for p in f.parents if (p / "Cargo.toml").exists()), f.parent) / "src"
    out = []
    for m in RS_USE.finditer(text):
        where = _rust_base(m, f, crate_root)
        hit = _rust_resolve(*where) if where else None
        if hit:
            out.append(hit)
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


def _java_index(files) -> dict:
    idx = {}
    for f in files:
        if f.suffix == ".java":
            parts = f.resolve().relative_to(ROOT).with_suffix("").parts
            for i in range(len(parts)):
                idx.setdefault("/".join(parts[i:]), f)
    return idx


def _edges_of(f: Path, py_idx, java_idx) -> list:
    lang = EXT[f.suffix]
    if lang == "python":
        return py_module_edges(f, py_idx)
    if lang == "js":
        return js_module_edges(f)
    return rust_module_edges(f) if lang == "rust" else java_module_edges(f, java_idx)


def module_graph(roots):
    files = list(source_files(roots))
    py_idx, java_idx = python_index(files), _java_index(files)
    edges = {(rel(f), rel(t)) for f in files for t in _edges_of(f, py_idx, java_idx) if t.resolve() != f.resolve()}
    return {rel(f) for f in files}, edges


# ---- function-level graph (Python) -----------------------------------------------------------------------

def parse_trees(files) -> dict:
    """file -> ast, for the files that parse."""
    trees = {}
    for f in files:
        try:
            trees[f] = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
    return trees


def _function_defs(trees: dict):
    """(nodes, defs): defs maps (file, simple or Class.name) -> qualified node name."""
    defs, nodes = {}, set()
    for f, tree in trees.items():
        for cls, fn in iter_functions(tree):
            q = f"{rel(f)}:{cls + '.' if cls else ''}{fn.name}"
            nodes.add(q); defs[(rel(f), fn.name)] = q
            if cls:
                defs[(rel(f), f"{cls}.{fn.name}")] = q
    return nodes, defs


def _call_edges(f, tree, py_idx, defs) -> set:
    imported = imported_names(tree, f, py_idx)
    edges = set()
    for cls, fn in iter_functions(tree):
        src = defs[(rel(f), f"{cls}.{fn.name}" if cls else fn.name)]
        for call in (n for n in ast.walk(fn) if isinstance(n, ast.Call)):
            tgt = resolve_call(call.func, rel(f), cls, imported, defs)
            if tgt and tgt != src:
                edges.add((src, tgt))
    return edges


def function_graph(roots):
    """Nodes `file:Class.method` / `file:func`; edges from calls resolved by name within the module, via
    imported names, and `self.method()` inside a class."""
    files = [f for f in source_files(roots) if f.suffix == ".py"]
    py_idx = python_index(files)
    trees = parse_trees(files)
    nodes, defs = _function_defs(trees)
    edges = set()
    for f, tree in trees.items():
        edges |= _call_edges(f, tree, py_idx, defs)
    return nodes, edges


FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)


def iter_functions(tree):
    """(class name or None, function node) for every top-level function and method, in file order."""
    for node in tree.body:
        if isinstance(node, FUNCTION_NODES):
            yield None, node
        elif isinstance(node, ast.ClassDef):
            yield from ((node.name, sub) for sub in node.body if isinstance(sub, FUNCTION_NODES))


def _from_import(node, pkg: list, py_idx, out: dict):
    base = ".".join(pkg[: len(pkg) - (node.level - 1)]) if node.level else ""
    mod = ".".join(x for x in (base, node.module or "") if x)
    target = resolve_py(mod, py_idx)
    if target:
        for a in node.names:
            out[a.asname or a.name] = (rel(target), a.name)


def _plain_import(node, py_idx, out: dict):
    for a in node.names:
        target = resolve_py(a.name, py_idx)
        if target:
            out[a.asname or a.name.split(".")[-1]] = (rel(target), None)


def imported_names(tree, f, py_idx):
    """local name -> (file, original name) for `from m import x` and `import m [as n]`."""
    out = {}
    pkg = list(f.resolve().relative_to(ROOT).parent.parts)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            _from_import(node, pkg, py_idx, out)
        elif isinstance(node, ast.Import):
            _plain_import(node, py_idx, out)
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
