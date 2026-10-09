"""Leaf over codefiles: the edges of the dependency graph. Module-level imports per language (Python, JS/TS, Rust,
Java, ABAP) resolved to project files, and Python call edges between functions. Unresolved imports are ignored, never
guessed. JavaScript/TypeScript and Rust are read by their own leaves (jsedges, rustedges); benchmark section 30
measures every language against a referee (grimp, dependency-cruiser, cargo-modules, jdeps)."""
import ast, re
from collections import defaultdict
from pathlib import Path

from bracecomments import strip_strings
from codefiles import ROOT, CODE_ROOTS, EXT, rel, source_files
from jsedges import js_module_edges
from rustedges import rust_module_edges


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


def _node_targets(node, pkg: list, idx) -> list:
    """The files one AST node imports: `import a.b`, `from .x import y`, a literal `importlib.import_module("a.b")`."""
    if isinstance(node, ast.Import):
        return [resolve_py(a.name, idx) for a in node.names]
    if isinstance(node, ast.ImportFrom):
        return _from_import_targets(node, pkg, idx)
    dynamic = _dynamic_import(node) if isinstance(node, ast.Call) else ""
    return [resolve_py(dynamic, idx)] if dynamic else []


def py_module_edges(f: Path, idx):
    """The project files a Python file imports (static imports and literal dynamic ones)."""
    try:
        tree = ast.parse(f.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    pkg = list(f.resolve().relative_to(ROOT).parent.parts)
    out = [t for node in ast.walk(tree) for t in _node_targets(node, pkg, idx)]
    return [t for t in out if t and t.resolve() != f.resolve()]


DYNAMIC_IMPORTS = ("importlib.import_module", "import_module", "__import__")


def _dynamic_import(call: ast.Call) -> str:
    """The module a literal `importlib.import_module("a.b")` or `__import__("a")` names, else ''."""
    fn = call.func
    name = fn.id if isinstance(fn, ast.Name) else (f"{fn.value.id}.{fn.attr}" if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) else "")
    first = call.args[0] if call.args else None
    if name in DYNAMIC_IMPORTS and isinstance(first, ast.Constant) and isinstance(first.value, str) and not first.value.startswith("."):
        return first.value
    return ""


JAVA_IMPORT = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)\s*;", re.M)


JAVA_PACKAGE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.M)
JAVA_WILDCARD = re.compile(r"^\s*import\s+(?:static\s+)?([\w.]+)\.\*\s*;", re.M)
JAVA_QUALIFIED = re.compile(r"(?<![\w.])((?:[a-z_]\w*\.)+[A-Z]\w*)")   # `com.acme.billing.Invoice` written in the code


def _java_package(text: str) -> str:
    m = JAVA_PACKAGE.search(text)
    return m.group(1) if m else ""


def _java_imports(text: str, paths: dict, used: set = None) -> list:
    """Explicit class imports resolved to project files (the longest path suffix that exists). With `used` (the
    names the code writes), an import whose class or member is never written (a Javadoc-only import) is no edge."""
    out = []
    for m in JAVA_IMPORT.finditer(text):
        parts = m.group(1).split(".")
        named = set(parts[-2:]) if "static" in m.group(0).split() else {parts[-1]}   # a static import names a member of a class
        if used is not None and not used & named:
            continue
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


def _java_qualified(code: str, paths: dict) -> list:
    """Classes named by their full name in the code, without an import: `new com.acme.billing.Invoice()`."""
    names = {m.group(1) for m in JAVA_QUALIFIED.finditer(code)}
    return [paths[k] for k in sorted("/".join(n.split(".")) for n in names) if k in paths and "/" in k]


def java_module_edges(f: Path, idx: dict):
    text = f.read_text(encoding="utf-8", errors="replace")
    code = strip_strings(text, "java")   # comments and string literals carry no references
    body = "\n".join(l for l in code.splitlines() if not l.lstrip().startswith(("import ", "package ")))
    out = _java_imports(text, idx["paths"], set(re.findall(r"\b\w+\b", body)))
    imported = {m.group(1).split(".")[-1] for m in JAVA_IMPORT.finditer(text)}   # a single-type import shadows the package's class
    visible = {n: v for n, v in _java_visible(text, idx).items() if n not in imported}
    named = set(re.findall(r"\b([A-Z]\w*)\b", body)) - {f.stem}
    return out + [visible[n] for n in sorted(named) if n in visible] + _java_qualified(body, idx["paths"])


def _java_index(files) -> dict:
    """paths: path suffix -> file (explicit imports); packages: package -> {Class: file} (same-package and wildcard use)."""
    idx = {"paths": {}, "packages": defaultdict(dict)}
    for f in [f for f in files if f.suffix == ".java"]:
        parts = f.resolve().relative_to(ROOT).with_suffix("").parts
        for i in range(len(parts)):
            idx["paths"].setdefault("/".join(parts[i:]), f)
        idx["packages"][_java_package(f.read_text(encoding="utf-8", errors="replace"))][f.stem] = f
    return idx


def _edges_of(f: Path, idx: dict, ownership: bool = True) -> list:
    lang = EXT[f.suffix]
    if lang == "python":
        return py_module_edges(f, idx["py"])
    if lang == "js":
        return js_module_edges(f)
    if lang == "abap":
        import abapdeps
        return abapdeps.module_edges(f, idx["abap"])
    return rust_module_edges(f, ownership) if lang == "rust" else java_module_edges(f, idx["java"])


def module_graph(roots, ownership: bool = True):
    """(nodes, edges) over the files of the roots; an ABAP object's part files fold into the file that stands for it.
    `ownership=False` leaves out Rust's `mod x;` declarations (a module declared is not a module used)."""
    import abapdeps
    files = list(source_files(roots))
    idx = {"py": python_index(files), "java": _java_index(files), "abap": abapdeps.index(files)}
    node_of = {f: rel(abapdeps.node_of(f, idx["abap"])) for f in files}
    nodes = set(node_of.values())
    edges = {(node_of[f], node_of.get(t, rel(t))) for f in files for t in _edges_of(f, idx, ownership) if node_of.get(t, rel(t)) != node_of[f] and node_of.get(t, rel(t)) in nodes}
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


