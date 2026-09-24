"""`aix code dead`: modules nobody imports and Python functions nobody names. Conservative by design (vulture's
rule): a decorated, exported, dunder, implicit or test function is live whatever the graph says."""
import ast, re
from collections import defaultdict
from pathlib import Path

from codefiles import ROOT, rel, source_files
from depedges import iter_functions, parse_trees
from graphmetrics import FACADE_NAMES, ROOT_STEMS, is_root_or_test, reach_sets


ENTRY_STEMS = ROOT_STEMS | {"manage", "wsgi", "asgi", "cli", "conftest", "setup", "settings", "config"}
ENTRY_SUFFIX = (".config.ts", ".config.js", ".config.mjs", ".d.ts")


JAVA_ENTRY = re.compile(r"static\s+void\s+main\s*\(|@(?:SpringBootApplication|SpringBootTest|Test|ParameterizedTest|Configuration|WebMvcTest|DataJpaTest)\b")


def has_main_guard(node: str) -> bool:
    """A file run or loaded on its own: a Python script (`if __name__ == "__main__":`), a Java class with `main` or a
    framework annotation (Spring Boot application or configuration, JUnit test)."""
    f = ROOT / node
    if not f.is_file() or f.suffix not in (".py", ".java"):
        return False
    text = f.read_text(encoding="utf-8", errors="replace")
    return '__name__ == "__main__"' in text if f.suffix == ".py" else bool(JAVA_ENTRY.search(text))


def is_entry_module(node: str) -> bool:
    """Modules nothing needs to import for them to be alive: entry points, tests, framework/tool config, scripts."""
    p = Path(node)
    return is_root_or_test(node) or p.stem.lower() in ENTRY_STEMS or p.name.endswith(ENTRY_SUFFIX) or p.name in FACADE_NAMES \
        or has_main_guard(node)


def dead_modules(nodes, edges):
    """Files no entry module reaches through imports. Reachability, not fan-in: an orphan cluster that imports
    each other is dead as a whole."""
    roots = {n for n in nodes if is_entry_module(n)}
    _, reach = reach_sets(nodes, edges)
    live = set(roots) | {x for r in roots for x in reach[r]}
    return roots, sorted(n for n in nodes if n not in live)


IMPLICIT_NAMES = {"main", "setup", "teardown", "setUp", "tearDown"}


def _exported_names(node) -> set:
    """The strings in an `__all__ = [...]` assignment, else nothing."""
    if isinstance(node, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "__all__" for x in node.targets):
        return {c.value for c in ast.walk(node.value) if isinstance(c, ast.Constant) and isinstance(c.value, str)}
    return set()


def _name_usage(trees: dict):
    """(used name -> count, names in __all__) over every parsed file."""
    used, exported = defaultdict(int), set()
    for node in (n for tree in trees.values() for n in ast.walk(tree)):
        if isinstance(node, ast.Name):
            used[node.id] += 1
        elif isinstance(node, ast.Attribute):
            used[node.attr] += 1
        else:
            exported |= _exported_names(node)
    return used, exported


def _live_by_rule(file: str, fn, exported: set) -> bool:
    """Entry modules, decorated functions, exports, implicit names, dunders and tests are called by something we cannot see."""
    name = fn.name
    return (is_entry_module(file) or bool(fn.decorator_list) or name in exported or name in IMPLICIT_NAMES
            or (name.startswith("__") and name.endswith("__")) or name.startswith("test"))


def dead_functions(roots):
    """Python functions/methods whose simple name is never referenced anywhere (as a bare name or an attribute)
    outside their own definition, are not decorated (routes, fixtures, commands are called by the framework),
    are not dunder/implicit, not in __all__, and not in an entry/test file. Same rule as vulture: name-based,
    so a method called through any object of the same name counts as live. Conservative by design."""
    trees = parse_trees([f for f in source_files(roots) if f.suffix == ".py"])
    used, exported = _name_usage(trees)
    dead = []
    for f, tree in trees.items():
        for cls, fn in iter_functions(tree):
            if not _live_by_rule(rel(f), fn, exported) and used[fn.name] == 0:  # a def is not an ast.Name, so any count is a real reference
                dead.append((f"{rel(f)}:{cls + '.' if cls else ''}{fn.name}", fn.lineno))
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
