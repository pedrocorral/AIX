"""Leaf over codefiles: the edges of the dependency graph. Module-level imports per language (Python, JS/TS, Rust,
Java) resolved to project files, and Python call edges between functions. Unresolved imports are ignored, never
guessed."""
import ast, json, re
from collections import defaultdict
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


JS_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".mjs")
_TS_CONFIGS = {}   # folder -> {"baseUrl": Path, "paths": {pattern: [targets]}} or None, once per run


def _jsonc(text: str):
    """tsconfig.json is JSON with comments and trailing commas."""
    text = re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.S)
    return json.loads(re.sub(r",\s*([}\]])", r"\1", text))


def _own_options(data: dict, cfg: Path) -> dict:
    """baseUrl (resolved) and paths declared in this file; paths without a baseUrl are relative to the file."""
    opts = data.get("compilerOptions") or {}
    out = {}
    if opts.get("baseUrl"):
        out["baseUrl"] = (cfg.parent / opts["baseUrl"]).resolve()
    if opts.get("paths"):
        out["paths"] = opts["paths"]
        out.setdefault("baseUrl", cfg.parent.resolve())
    return out


def _linked_configs(data: dict, cfg: Path) -> list:
    """The files `extends` and (solution-style tsconfigs) `references` point to."""
    links = ([data["extends"]] if isinstance(data.get("extends"), str) else []) + [r.get("path", "") for r in data.get("references", [])]
    return [(cfg.parent / (link if link.endswith(".json") else link + "/tsconfig.json")).resolve() for link in links if link]


def _ts_options(cfg: Path, seen: set = None) -> dict:
    """baseUrl and paths of a tsconfig, following `extends` and `references`; the nearest declaration wins."""
    seen = seen or set()
    if cfg in seen or not cfg.is_file():
        return {}
    seen.add(cfg)
    try:
        data = _jsonc(cfg.read_text(encoding="utf-8", errors="replace"))
    except ValueError:
        return {}
    out = _own_options(data, cfg)
    for linked in _linked_configs(data, cfg):
        for k, v in _ts_options(linked, seen).items():
            out.setdefault(k, v)
    return out


def _ts_config_for(f: Path) -> dict:
    """The options of the nearest tsconfig.json / jsconfig.json at or above the file, inside the project."""
    for folder in [f.parent, *f.parent.parents]:
        if folder in _TS_CONFIGS:
            return _TS_CONFIGS[folder]
        cfg = next((folder / n for n in ("tsconfig.json", "jsconfig.json") if (folder / n).is_file()), None)
        if cfg or folder == ROOT.resolve() or not folder.is_relative_to(ROOT.resolve()):
            _TS_CONFIGS[folder] = _ts_options(cfg) if cfg else {}
            return _TS_CONFIGS[folder]
    return {}


def _alias_bases(spec: str, f: Path) -> list:
    """Where a bare specifier may live: tsconfig `paths` patterns (`@/*` -> `src/*`), then `baseUrl` itself."""
    cfg = _ts_config_for(f)
    if not cfg:
        return []
    bases = []
    for pattern, targets in (cfg.get("paths") or {}).items():
        prefix = pattern.split("*")[0]
        if spec.startswith(prefix) and (("*" in pattern) or spec == pattern):
            rest = spec[len(prefix):]
            bases += [cfg["baseUrl"] / t.replace("*", rest) for t in targets]
    return bases + [cfg["baseUrl"] / spec]


def _resolve_js(base: Path):
    cands = [base] + [base.with_suffix(e) for e in JS_SUFFIXES] + [base / f"index{e}" for e in JS_SUFFIXES]
    return next((c for c in cands if c.is_file()), None)


def js_module_edges(f: Path):
    out = []
    for m in JS_IMPORT.finditer(f.read_text(encoding="utf-8", errors="replace")):
        spec = next(g for g in m.groups() if g)
        bases = [f.parent / spec] if spec.startswith(".") else _alias_bases(spec, f)
        hit = next((h for h in map(_resolve_js, bases) if h), None)
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


JAVA_PACKAGE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.M)
JAVA_WILDCARD = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)\.\*\s*;", re.M)
JAVA_NOISE = re.compile(r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\])*\"", re.S)   # comments and string literals carry no references


def _java_package(text: str) -> str:
    m = JAVA_PACKAGE.search(text)
    return m.group(1) if m else ""


def _java_imports(text: str, paths: dict) -> list:
    """Explicit class imports resolved to project files (the longest path suffix that exists)."""
    out = []
    for m in JAVA_IMPORT.finditer(text):
        parts = m.group(1).split(".")
        hit = next((paths[k] for n in range(len(parts), 0, -1) if (k := "/".join(parts[:n])) in paths), None)
        if hit:
            out.append(hit)
    return out


def _java_visible(text: str, idx: dict) -> dict:
    """Class -> file for the classes a Java file may name without importing them: its own package and the packages
    it imports with `.*`."""
    visible = dict(idx["packages"].get(_java_package(text), {}))
    for m in JAVA_WILDCARD.finditer(text):
        visible.update(idx["packages"].get(m.group(1), {}))
    return visible


def java_module_edges(f: Path, idx: dict):
    text = f.read_text(encoding="utf-8", errors="replace")
    out = _java_imports(text, idx["paths"])
    visible = _java_visible(text, idx)
    named = set(re.findall(r"\b([A-Z]\w*)\b", JAVA_NOISE.sub(" ", text))) - {f.stem}
    return out + [visible[n] for n in sorted(named) if n in visible]


def _java_index(files) -> dict:
    """paths: path suffix -> file (explicit imports); packages: package -> {Class: file} (same-package and wildcard use)."""
    idx = {"paths": {}, "packages": defaultdict(dict)}
    for f in [f for f in files if f.suffix == ".java"]:
        parts = f.resolve().relative_to(ROOT).with_suffix("").parts
        for i in range(len(parts)):
            idx["paths"].setdefault("/".join(parts[i:]), f)
        idx["packages"][_java_package(f.read_text(encoding="utf-8", errors="replace"))][f.stem] = f
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
    nodes = {rel(f) for f in files}
    edges = {(rel(f), rel(t)) for f in files for t in _edges_of(f, py_idx, java_idx) if t.resolve() != f.resolve() and rel(t) in nodes}
    return nodes, edges  # an import of an asset (lock.svg, package.json) or of a file outside the roots is not an edge


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


FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)


def iter_functions(tree):
    """(class name or None, function node) for every top-level function and method, in file order."""
    for node in tree.body:
        if isinstance(node, FUNCTION_NODES):
            yield None, node
        elif isinstance(node, ast.ClassDef):
            yield from ((node.name, sub) for sub in node.body if isinstance(sub, FUNCTION_NODES))


