"""Leaf: the defensive-programming facts of one Python file, for `aix code defensive`. Annotations (fully typed,
untyped), pydantic (models, strict ones, value rules, validators, validate_call), the doors (outside data read by
json/yaml/toml/pickle loads, Flask and Django request attributes, FastAPI handler parameters) and whether the
value is checked before use, and the inside findings: an assert in production code, `open()` without `with`
and without a close, None returned under an annotation that promises a value."""
import ast, re

FUNCS = (ast.FunctionDef, ast.AsyncFunctionDef)
SCOPES = FUNCS + (ast.ClassDef,)
MODEL_BASES = {"BaseModel", "BaseSettings", "SQLModel", "RootModel"}
RULE_KEYS = {"gt", "ge", "lt", "le", "min_length", "max_length", "pattern", "regex", "multiple_of", "max_digits", "decimal_places", "strict"}
VALIDATORS = {"field_validator", "model_validator", "validator", "root_validator"}
DOOR_CALLS = {"json.load", "json.loads", "yaml.safe_load", "yaml.load", "yaml.full_load", "tomllib.load", "tomllib.loads", "toml.load", "toml.loads",
              "request.get_json", "pickle.load", "pickle.loads"}
DOOR_ATTRS = re.compile(r"(?:^|\.)(request\.(?:form|args|json|POST|GET|data|values|files))$")
GUARD_TAILS = {"model_validate", "model_validate_json", "validate_python", "validate_json", "parse_obj", "parse_raw", "isinstance", "int", "float", "TypeAdapter"}
HANDLER_DECOS = {"get", "post", "put", "delete", "patch", "route", "api_route", "websocket"}
HANDLER_FREE = {"self", "cls", "request", "response", "background_tasks", "websocket"}
STRICT = re.compile(r"\bstrict\s*=\s*True\b")


def dotted(node) -> str:
    """`a.b.c` for a Name/Attribute chain, the callee of a Call, "" for anything else."""
    if isinstance(node, ast.Attribute):
        return dotted(node.value) + "." + node.attr
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Call):
        return dotted(node.func)
    return ""


def _tail(node) -> str:
    return dotted(node).split(".")[-1]


def _own_nodes(fn, node=None, ancestors=()):
    """(node, ancestors) over a function's own code: nested functions and classes are not descended into."""
    node = fn if node is None else node
    yield node, ancestors
    for child in ast.iter_child_nodes(node):
        if not isinstance(child, SCOPES):
            yield from _own_nodes(fn, child, ancestors + (node,))


def _params(fn) -> list:
    return [a for a in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs if a.arg not in ("self", "cls")]


def imports(tree, package: str) -> bool:
    """Whether the module imports `package` or something from it."""
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] == package:
            return True
        if isinstance(n, ast.Import) and any(a.name.split(".")[0] == package for a in n.names):
            return True
    return False


# ---- annotations ------------------------------------------------------------------------------------------------

def annotation_counts(fns) -> dict:
    """fully typed: every parameter and the return annotated; untyped: parameters, none of them annotated."""
    full = untyped = 0
    for fn in fns:
        ps = _params(fn)
        full += fn.returns is not None and all(a.annotation is not None for a in ps)
        untyped += bool(ps) and not any(a.annotation is not None for a in ps)
    return {"funcs": len(fns), "full": full, "untyped": untyped}


# ---- pydantic ---------------------------------------------------------------------------------------------------

def _is_model(cls) -> bool:
    return any(_tail(b) in MODEL_BASES for b in cls.bases)


def _strict_model(cls) -> bool:
    """`model_config = ConfigDict(strict=True)` or `class Config: strict = True` in the class body."""
    for stmt in cls.body:
        if isinstance(stmt, ast.Assign) and any(dotted(t) == "model_config" for t in stmt.targets) and STRICT.search(ast.unparse(stmt)):
            return True
        if isinstance(stmt, ast.ClassDef) and stmt.name == "Config" and STRICT.search(ast.unparse(stmt)):
            return True
    return False


def _field_rules(cls) -> int:
    return sum(1 for n in ast.walk(cls) if isinstance(n, ast.Call) and _tail(n) == "Field" and any(k.arg in RULE_KEYS for k in n.keywords))


def _validators(cls) -> int:
    return sum(1 for stmt in cls.body if isinstance(stmt, FUNCS) and any(_tail(d) in VALIDATORS for d in stmt.decorator_list))


def _validate_calls(fns) -> tuple:
    """(functions under validate_call, those with strict=True)."""
    decos = [d for fn in fns for d in fn.decorator_list if _tail(d) == "validate_call"]
    return len(decos), sum(1 for d in decos if isinstance(d, ast.Call) and STRICT.search(ast.unparse(d)))


def pydantic_facts(tree, fns) -> dict:
    models = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and _is_model(n)]
    calls, strict_calls = _validate_calls(fns)
    return {"pydantic": imports(tree, "pydantic"), "models": len(models), "strict_models": sum(map(_strict_model, models)),
            "rules": sum(map(_field_rules, models)), "validators": sum(map(_validators, models)), "calls": calls, "strict_calls": strict_calls}


# ---- doors ------------------------------------------------------------------------------------------------------

def _door(node) -> str:
    """The outside-data read this node is ("json.load", "request.form"), or ""."""
    if isinstance(node, ast.Call) and dotted(node) in DOOR_CALLS:
        return dotted(node)
    m = DOOR_ATTRS.search(dotted(node)) if isinstance(node, ast.Attribute) else None
    return m.group(1) if m else ""


def _is_guard(call) -> bool:
    """A call that checks or parses its argument: a constructor (`Config(**data)`), a pydantic parse, isinstance, int, float."""
    tail = _tail(call)
    return tail in GUARD_TAILS or (tail[:1].isupper() and tail != tail.upper())


def _guard_args(call) -> set:
    return {n.id for a in call.args + [k.value for k in call.keywords] for n in ast.walk(a) if isinstance(n, ast.Name)}


def _assigned_name(ancestors) -> str:
    """The single name a statement assigns, when the door's value lands in one."""
    stmt = next((a for a in reversed(ancestors) if isinstance(a, ast.stmt)), None)
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
        return stmt.targets[0].id
    return stmt.target.id if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) else ""


def _checked(fn, ancestors, guard_calls) -> bool:
    if any(isinstance(a, ast.Call) and _is_guard(a) for a in ancestors):
        return True
    name = _assigned_name(ancestors)
    return bool(name) and any(name in _guard_args(c) for c in guard_calls)


def door_spots(fn) -> tuple:
    """(doors, [(line, what)] for the unchecked ones) over the outside-data reads of one function."""
    guard_calls = [n for n, _ in _own_nodes(fn) if isinstance(n, ast.Call) and _is_guard(n)]
    doors, bad = 0, []
    for node, ancestors in _own_nodes(fn):
        what = _door(node)
        if what:
            doors += 1
            if not _checked(fn, ancestors, guard_calls):
                bad.append((node.lineno, f"{what}{'(...)' if isinstance(node, ast.Call) else ''} reaches the code unchecked"))
    return doors, bad


def handler_params(fn, fastapi: bool) -> tuple:
    """(parameters, [(line, what)] for the untyped ones) of a FastAPI handler: the framework checks what is typed."""
    if not fastapi or not any(_tail(d) in HANDLER_DECOS for d in fn.decorator_list):
        return 0, []
    ps = [a for a in _params(fn) if a.arg not in HANDLER_FREE]
    return len(ps), [(fn.lineno, f"{fn.name}(): parameter `{a.arg}` has no type, it arrives unchecked") for a in ps if a.annotation is None]


# ---- inside -----------------------------------------------------------------------------------------------------

def assert_lines(fn) -> list:
    return [n.lineno for n, _ in _own_nodes(fn) if isinstance(n, ast.Assert)]


def _closed(fn, name: str) -> bool:
    return any(isinstance(n, ast.Call) and dotted(n) == f"{name}.close" for n, _ in _own_nodes(fn))


def open_spots(fn) -> list:
    """Lines of a bare `open()` that is neither a `with` item, nor returned (handed to the caller), nor assigned to a
    name that is closed in the function."""
    out = []
    for node, ancestors in _own_nodes(fn):
        if isinstance(node, ast.Call) and dotted(node) in ("open", "io.open") and not isinstance(ancestors[-1], (ast.withitem, ast.Return)) \
                and not _closed(fn, _assigned_name(ancestors)):
            out.append(node.lineno)
    return out


def _is_none(value) -> bool:
    if value is None or (isinstance(value, ast.Constant) and value.value is None):
        return True
    return isinstance(value, ast.IfExp) and (_is_none(value.body) or _is_none(value.orelse))


def _has_value(value) -> bool:
    """A return that carries a value on some path (`return "a"`, `return None if x else "a"`)."""
    if isinstance(value, ast.IfExp):
        return _has_value(value.body) or _has_value(value.orelse)
    return not _is_none(value)


def _if_falls_off(last) -> bool:
    return not last.orelse or _falls_off(last.body) or _falls_off(last.orelse)


def _try_falls_off(last) -> bool:
    body = _falls_off(last.body) or any(_falls_off(h.body) for h in last.handlers)
    return body and (not last.finalbody or _falls_off(last.finalbody))


def _while_falls_off(last) -> bool:
    return not (isinstance(last.test, ast.Constant) and last.test.value is True)


def _match_falls_off(last) -> bool:
    wildcard = any(isinstance(c.pattern, ast.MatchAs) and c.pattern.pattern is None for c in last.cases)
    return not wildcard or any(_falls_off(c.body) for c in last.cases)


EXITS = {"sys.exit", "exit", "quit", "os._exit", "os.abort"}


def _expr_falls_off(last) -> bool:
    return not (isinstance(last.value, ast.Call) and dotted(last.value) in EXITS)


ENDS = {ast.Return: lambda _: False, ast.Raise: lambda _: False, ast.If: _if_falls_off, ast.Try: _try_falls_off, ast.Expr: _expr_falls_off,
        ast.With: lambda last: _falls_off(last.body), ast.While: _while_falls_off, ast.Match: _match_falls_off}


def _falls_off(stmts: list) -> bool:
    """Whether running the statements can reach their end without a return or a raise."""
    if not stmts:
        return True
    return ENDS.get(type(stmts[-1]), lambda _: True)(stmts[-1])


def _none_lines(fn, rets: list) -> list:
    """The lines where the function hands back None: each such return, and the end when it can be reached."""
    lines = [(r.lineno, "returns None") for r in rets if _is_none(r.value)]
    if _falls_off(fn.body):
        lines.append((fn.body[-1].end_lineno, "falls off the end"))
    return lines


def return_spots(fn) -> list:
    """(line, what) for each None returned, and the fall-off, by a function whose annotation promises a value and
    that returns a value somewhere; `-> X | None`, `Optional[X]`, `Any`, `object`, `-> None` and stubs without a value are honest."""
    if fn.returns is None or re.search(r"\bNone\b|\bOptional\b|\bAny\b|\bobject\b", ast.unparse(fn.returns)):
        return []
    rets = [n for n, _ in _own_nodes(fn) if isinstance(n, ast.Return)]
    if not any(_has_value(r.value) for r in rets):
        return []
    return [(fn.lineno, f"{fn.name}(): {how} (line {line}) under `-> {ast.unparse(fn.returns)}`") for line, how in _none_lines(fn, rets)]


# ---- one file ---------------------------------------------------------------------------------------------------

def _spots_of(fn, fastapi: bool, facts: dict) -> list:
    """(kind, line, what) of one function; the door and handler counts are added to the facts."""
    doors, bad = door_spots(fn)
    params, untyped = handler_params(fn, fastapi)
    facts["doors"] += doors + params
    facts["unchecked"] += len(bad) + len(untyped)
    spots = [("DOOR", line, what) for line, what in bad + untyped]
    spots += [("ASSERT", line, "assert as a check") for line in assert_lines(fn)]
    spots += [("OPEN", line, "open() without `with` and no close()") for line in open_spots(fn)]
    return spots + [("RETURN", line, what) for line, what in return_spots(fn)]


def scan(text: str):
    """The facts of one file: counts and the (kind, line, what) spots; None when the file does not parse."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    fns = [n for n in ast.walk(tree) if isinstance(n, FUNCS)]
    facts = annotation_counts(fns)
    facts.update(pydantic_facts(tree, fns), doors=0, unchecked=0)
    fastapi = imports(tree, "fastapi")
    facts["spots"] = [s for fn in fns for s in _spots_of(fn, fastapi, facts)]
    return facts
