"""Leaf: the Python call graph by AST. Nodes `file:Class.method` / `file:func`; an arc when a call resolves by name:
a function of the same file, a name imported by name, `self.m()` inside a class, `module.f()` through a module
import, `Thing(...)` to `Thing.__init__`, and a name a package re-exports through its `__init__`. RESOLUTION counts
the calls that could target project code and those matched; the report prints the ratio."""
import ast

from codefiles import ROOT, rel, source_files
from depedges import iter_functions, parse_trees, python_index, resolve_py


def _function_defs(trees: dict):
    """(nodes, defs): defs maps (file, simple or Class.name) -> qualified node name; a class with no `__init__` maps
    its name to None, so `Thing(...)` is neither an arc nor a miss."""
    defs, nodes = {}, set()
    for f, tree in trees.items():
        for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
            defs.setdefault((rel(f), cls.name), None)
        for cls, fn in iter_functions(tree):
            q = f"{rel(f)}:{cls + '.' if cls else ''}{fn.name}"
            nodes.add(q); defs[(rel(f), fn.name)] = q
            if cls:
                defs[(rel(f), f"{cls}.{fn.name}")] = q
    return nodes, defs


RESOLUTION = {"seen": 0, "matched": 0}   # calls that could target project code, and those matched, by the last function_graph


BUILTINS = set(dir(__builtins__)) if isinstance(__builtins__, dict) is False else set(__builtins__)


def _nested_defs(fn) -> set:
    """Names that are values inside this function, not functions of the project: nested functions and classes,
    parameters, and local variables (a callback called by its parameter name is nobody's node)."""
    nested = {n.name for n in ast.walk(fn) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n is not fn}
    params = {a.arg for a in fn.args.args + fn.args.kwonlyargs + fn.args.posonlyargs} | {a.arg for a in (fn.args.vararg, fn.args.kwarg) if a}
    stored = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    return nested | params | stored


def _external_names(tree) -> set:
    """Local names bound by imports of packages outside the project: their calls are outside A, not misses."""
    return {(a.asname or a.name).split(".")[0] for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names}


def _could_be_project_call(func, imported: dict, externals: set = frozenset()) -> bool:
    """A plain name that is no builtin and no library import, `self.m()`, or `module.f()` through a project import:
    what name resolution can hope to match. `x.strip()` or `re.search()` are outside A by construction, not misses."""
    if isinstance(func, ast.Name):
        return func.id not in BUILTINS and (func.id in imported or func.id not in externals)
    module = isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id in imported and imported[func.value.id][1] is None
    return module or (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "self")


def _call_edges(f, tree, py_idx, defs) -> set:
    imported, externals = imported_names(tree, f, py_idx), _external_names(tree)
    edges = set()
    for cls, fn in iter_functions(tree):
        src = defs[(rel(f), f"{cls}.{fn.name}" if cls else fn.name)]
        local = _nested_defs(fn)
        for call in (n for n in ast.walk(fn) if isinstance(n, ast.Call) and _could_be_project_call(n.func, imported, externals | local)):
            tgt = resolve_call(call.func, rel(f), cls, imported, defs)
            if tgt is SKIP:
                continue
            RESOLUTION["seen"] += 1
            RESOLUTION["matched"] += bool(tgt)
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
    REEXPORTS.clear()
    REEXPORTS.update({rel(f): imported_names(tree, f, py_idx) for f, tree in trees.items()})
    edges = set()
    RESOLUTION.update(seen=0, matched=0)
    for f, tree in trees.items():
        edges |= _call_edges(f, tree, py_idx, defs)
    return nodes, edges


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


REEXPORTS = {}   # file -> its imported names, so a package's `__init__` can hand a name on to where it is defined
SKIP = object()  # a class with no __init__: not an arc, not a miss


def _named(defs, file, name):
    """A function of that name, a class through its `__init__` (`Thing(...)` calls it), or what a facade re-exports."""
    if (file, name) in defs:
        return defs[(file, name)] or defs.get((file, f"{name}.__init__")) or SKIP
    via = REEXPORTS.get(file, {}).get(name)
    return _named(defs, via[0], via[1] or name) if via and via[0] != file else None


def resolve_call(func, file, cls, imported, defs):
    if isinstance(func, ast.Name):
        if func.id in imported and imported[func.id][1]:
            return _named(defs, *imported[func.id])
        return _named(defs, file, func.id)
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            if func.value.id == "self" and cls:
                return defs.get((file, f"{cls}.{func.attr}"))
            if func.value.id in imported and imported[func.value.id][1] is None:
                return _named(defs, imported[func.value.id][0], func.attr)
            return defs.get((file, f"{func.value.id}.{func.attr}"))
    return None
