"""Leaf: modernisation advice, only what the detected runtime allows (match statements, `X | None`, dataclasses,
pathlib, tomllib for Python; optional chaining, nullish coalescing, const/let for JS; let-else for Rust; switch
expressions for Java)."""
import ast, re


# ---- modernisation: only what the detected runtime allows ---------------------------------------------------------

def _py_at_least(rt, major, minor):
    v = rt.get("python", (None,))[0]
    return v is not None and v >= (major, minor)


def _typing_names(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}


def _typing_hints(fn) -> set:
    names = set()
    for a in [a for a in fn.args.args + fn.args.kwonlyargs if a.annotation]:
        names |= _typing_names(a.annotation)
    return names | (_typing_names(fn.returns) if fn.returns else set())


def _modern_310(fn, out: list):
    if any(isinstance(n, ast.If) and _elif_ladder_on_one_name(n) >= 3 for n in ast.walk(fn)):
        node = next(n for n in ast.walk(fn) if isinstance(n, ast.If) and _elif_ladder_on_one_name(n) >= 3)
        out.append((node.lineno, "if/elif ladder comparing one value", "a `match` statement (Python 3.10+) reads as a table and cuts nesting"))
    names = _typing_hints(fn)
    if "Optional" in names or "Union" in names:
        out.append((fn.lineno, "`Optional[...]` / `Union[...]` in the signature", "write `X | None` and `A | B` (Python 3.10+)"))
    if names & {"List", "Dict", "Set", "Tuple", "FrozenSet", "Type"}:
        out.append((fn.lineno, "`typing.List/Dict/Set/Tuple` in the signature", "use the builtins `list[...]`, `dict[...]` (Python 3.9+)"))


def _only_assigns_parameters(fn) -> bool:
    return bool(fn.body) and all(isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Attribute)
                                 and isinstance(s.value, ast.Name) for s in fn.body)


def _os_path_use(fn):
    for node in ast.walk(fn):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name) \
                and node.value.value.id == "os" and node.value.attr == "path":
            return node
    return None


def _modern_311(fn, out: list):
    for node in ast.walk(fn):
        if isinstance(node, ast.Import) and any(a.name in ("toml", "tomli") for a in node.names):
            out.append((node.lineno, "`import toml/tomli`", "`tomllib` is in the standard library (Python 3.11+)"))


def _dataclass_candidate(fx) -> bool:
    return fx["fname"] == "__init__" and bool(fx["cls"]) and _only_assigns_parameters(fx["node"])


def modern_py(fx, rt):
    """(line, what, advice) modernisations the detected Python version allows."""
    fn, out = fx["node"], []
    if _py_at_least(rt, 3, 10):
        _modern_310(fn, out)
    if _py_at_least(rt, 3, 7) and _dataclass_candidate(fx):
        out.append((fn.lineno, "`__init__` that only assigns its parameters", f"`@dataclass` on `{fx['cls']}` removes it (Python 3.7+)"))
    node = _os_path_use(fn)
    if node:
        out.append((node.lineno, f"`os.path.{node.attr}`", "`pathlib.Path` reads as objects, not string plumbing"))
    if _py_at_least(rt, 3, 11):
        _modern_311(fn, out)
    return out


def _compared_name(test):
    """The NAME in a test of the form `NAME == constant`, else None."""
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq) \
            and isinstance(test.left, ast.Name) and isinstance(test.comparators[0], ast.Constant):
        return test.left.id
    return None


def _elif_ladder_on_one_name(node) -> int:
    """Length of an if/elif chain whose every test is `NAME == constant` on the same NAME (else 0)."""
    name, count = None, 0
    while isinstance(node, ast.If):
        this = _compared_name(node.test)
        if this is None or (name is not None and this != name):
            return 0
        name, count = this, count + 1
        node = node.orelse[0] if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If) else None
    return count


def _modern_js(src: str, es, line_of) -> list:
    out = []
    if es and es[0] >= 2020:
        m = re.search(r"\b([A-Za-z_$][\w$.]*)\s*&&\s*\1\.", src)
        if m:
            out.append((line_of(m), f"`{m.group(1)} && {m.group(1)}.…`", "optional chaining `?.` (ES2020)"))
        m = re.search(r"\b([A-Za-z_$][\w$.]*)\s*!==?\s*(?:undefined|null)\s*\?\s*\1\s*:", src)
        if m:
            out.append((line_of(m), f"`{m.group(1)} !== undefined ? {m.group(1)} : …`", "nullish coalescing `??` (ES2020)"))
    m = re.search(r"\bvar\s+\w", src)
    if es and es[0] >= 2015 and m:
        out.append((line_of(m), "`var`", "`const`/`let` have block scope (ES2015)"))
    return out


def _modern_rust(src: str, v, line_of) -> list:
    m = re.search(r"match\s+[^{]+\{\s*(?:Some|Ok)\((\w+)\)\s*=>\s*\1\s*,\s*(?:None|Err\([^)]*\))\s*=>\s*(?:return|continue|break)", src) if v and v >= (1, 65) else None
    return [(line_of(m), "match that only unwraps or returns", "`let … else` (Rust 1.65+)")] if m else []


def _modern_java(src: str, v, line_of) -> list:
    m = re.search(r"\bswitch\s*\(", src)
    if v and v[0] >= 14 and m and "->" not in src and re.search(r"\bbreak\s*;", src):
        return [(line_of(m), "switch with `break`s", "switch expression with `->` (Java 14+)")]
    return []


def modern_tokens(fx, rt):
    src, lang = fx.get("src", ""), fx["lang"]
    line_of = lambda m: fx["line"] + src.count("\n", 0, m.start())
    checks = {"js": _modern_js, "rust": _modern_rust, "java": _modern_java}
    if lang not in checks:
        return []
    return checks[lang](src, rt.get(lang, (None,))[0], line_of)


def modernisations(fx, rt):
    return modern_py(fx, rt) if fx["lang"] == "python" else modern_tokens(fx, rt)
