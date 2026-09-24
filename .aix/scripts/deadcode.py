"""`aix code dead`: modules nobody imports and Python functions nobody names. Conservative by design (vulture's
rule): a decorated, exported, dunder, implicit or test function is live whatever the graph says."""
import ast, re
from collections import defaultdict
from pathlib import Path

from codefiles import ROOT, rel, source_files
from depedges import iter_functions, parse_trees
from graphmetrics import FACADE_NAMES, ROOT_STEMS, is_root_or_test, reach_sets


ENTRY_STEMS = ROOT_STEMS | {"manage", "wsgi", "asgi", "cli", "conftest", "setup", "settings", "config", "lib", "build", "apps", "admin", "urls",
                            "gruntfile", "gulpfile", "service-worker", "sw", "karma.conf", "protractor.conf"}
ENTRY_SUFFIX = (".config.ts", ".config.js", ".config.mjs", ".config.cjs", ".d.ts", "rc.js", "rc.cjs", "rc.mjs")
ENTRY_FOLDERS = {"migrations", "benches", "examples", "scripts", "bin", "it", "commands", "management", "public", "static", "hooks"}
# loaded by convention, not by import: Django migrations/admin/apps/management commands, Cargo lib/build/benches/examples/bin,
# Maven's src/it, tool scripts and static assets (a service worker), git hooks


JAVA_ENTRY = re.compile(r"static\s+void\s+main\s*\(|@(?:SpringBootApplication|SpringBootTest|SpringBootConfiguration|Test|ParameterizedTest|RepeatedTest|TestConfiguration|"
                        r"Configuration|WebMvcTest|WebFluxTest|DataJpaTest|Controller|RestController|ControllerAdvice|RestControllerAdvice|Component|Service|Repository|Entity|"
                        r"Aspect|Named|ApplicationScoped|Path|Provider|WebFilter|WebServlet|WebListener|Scheduled|EventListener|KafkaListener|RabbitListener|JmsListener)\b")
# the container instantiates these itself: Spring, Jakarta CDI, JAX-RS, servlets, JUnit


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
        or p.name.startswith(".") or bool(ENTRY_FOLDERS & set(p.parts[:-1])) or has_main_guard(node)


PATH_LITERAL = re.compile(r"""['"](?:\./)?((?=[\w.@/-]*/)[\w@][\w.@-]*(?:/[\w.@-]+)*/?)['"]""")   # a literal with a slash: a path


def data_folders(nodes) -> set:
    """Folders a string literal in code names (`'data/static/codefixes'`, `'./fixtures/'`): their files are loaded as
    data (read, listed, served), not imported. Relative to the project root or to the file naming them."""
    out = set()
    for n in nodes:
        f = ROOT / n
        if f.suffix not in (".py", ".js", ".jsx", ".ts", ".tsx", ".mjs"):
            continue
        for m in PATH_LITERAL.finditer(f.read_text(encoding="utf-8", errors="replace")):
            for base in (ROOT, f.parent):
                folder = (base / m.group(1)).resolve()
                if folder.is_dir() and folder != ROOT.resolve() and folder.is_relative_to(ROOT.resolve()):
                    out.add(rel(folder))
    return out


def dead_modules(nodes, edges):
    """(entry modules, dead files, data folders): files no entry module reaches through imports and that no
    string in code names as a folder. Reachability, not fan-in: an orphan cluster importing each other is dead."""
    roots = {n for n in nodes if is_entry_module(n)}
    _, reach = reach_sets(nodes, edges)
    data = data_folders(nodes)
    live = set(roots) | {x for r in roots for x in reach[r]} | {n for n in nodes if any(n.startswith(d + "/") for d in data)}
    return roots, sorted(n for n in nodes if n not in live), data


IMPLICIT_NAMES = {"main", "setup", "teardown", "setUp", "tearDown"}


def _exported_names(node) -> set:
    """The strings in an `__all__ = [...]` assignment, else nothing."""
    if isinstance(node, ast.Assign) and any(isinstance(x, ast.Name) and x.id == "__all__" for x in node.targets):
        return {c.value for c in ast.walk(node.value) if isinstance(c, ast.Constant) and isinstance(c.value, str)}
    return set()


def _count_imported(node, used: dict):
    """`from .api import delete` re-exports a function: that is a use."""
    for alias in node.names:
        used[alias.name] += 1


def _name_usage(trees: dict):
    """(used name -> count, names in __all__) over every parsed file."""
    used, exported = defaultdict(int), set()
    for node in (n for tree in trees.values() for n in ast.walk(tree)):
        if isinstance(node, ast.Name):
            used[node.id] += 1
        elif isinstance(node, ast.Attribute):
            used[node.attr] += 1
        elif isinstance(node, ast.ImportFrom):
            _count_imported(node, used)
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
    roots, dead, data = dead_modules(nodes, edges)
    lines = ["", f"Dead code — {', '.join(paths)}", "",
             f"  entry modules (live by definition): {len(roots)}  e.g. " + ", ".join(sorted(roots)[:6])]
    if data:
        lines.append("  loaded as data (a folder named by a string in code, its files read, not imported): " + ", ".join(sorted(data)[:8]))
    lines.append(f"  DEAD MODULES {len(dead)}  (no entry module reaches them through imports)")
    lines += [f"    {n}" for n in dead[:40]]
    if functions:
        df = dead_functions(paths)
        lines += [f"  DEAD FUNCTIONS {len(df)}  (Python: name never referenced outside its definition; decorated, dunder, exported and entry/test code excluded)"]
        lines += [f"    {q}  (line {ln})" + ("" if q.rsplit(".", 1)[-1].split(":")[-1].startswith("_") else "  (public: the API of a library, or dead in an application)") for q, ln in df[:60]]
    else:
        lines.append("  (add --functions for Python dead functions and methods)")
    lines.append("  Every line is a candidate: confirm nothing reaches it by string, reflection or a framework before deleting. Fix with: skill refactor-dead")
    lines.append("  Live by convention: tests, main/lib/build, Django migrations/admin/apps/commands, Cargo benches/examples/bin, Maven src/it, scripts/, public/,")
    lines.append("  dot-files, *.config.*, container-managed Java classes (@Controller, @Service, @Entity, ...), folders named by a string in code.")
    return "\n".join(lines), len(dead) + (len(df) if functions else 0)
