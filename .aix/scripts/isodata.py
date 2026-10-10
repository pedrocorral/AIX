"""Leaf: the data boundaries of the isolation declaration. A `data:` entry names the fields that carry one kind of
data and where it may live:

    data:
      card: {fields: [card_number, cvv], stays_in: [payments], never_to: [logs, http, print]}

Two checks, both reported as DATA findings:
  outside    a field written (as a name, an attribute or a string key) in a file of an isolation that is not one of
             `stays_in` (or a part of one): the data left its boundary
  sink       a field reaching a sink, anywhere: a logger, print, or an outbound HTTP call (`never_to`, all three
             when absent). Python follows the value through local assignments in the function (the taint walk
             reversed: the source is the field, the sink is where it must never go); JS/TS, Java and Rust read the
             statement (the field and the sink in one call).
Comments never count. A field name that is also an everyday word (`id`, `name`) makes noise: name the fields as
the data model names them (field-dictionary.md)."""
import ast, io, re, tokenize
from pathlib import Path

from bracecomments import strip_comments
from codefiles import EXT
from isodecl import _as_list
from taint import call_name

SINK_CALLS = {
    "logs": re.compile(r"(?:^|\.)(?:debug|info|warning|warn|error|exception|critical|fatal|trace|log)$"),
    "http": re.compile(r"^(?:requests|httpx|aiohttp|urllib3?)\.|(?:^|\.)(?:urlopen|post|put|patch|request|send)$"),
    "print": re.compile(r"^(?:print|pprint|pprint\.pprint|sys\.stdout\.write|sys\.stderr\.write)$"),
}
LOG_RECEIVER = re.compile(r"(?:^|\.)(?:logging|logger|log|_log|_logger|LOG|LOGGER|console)\.")
BRACE_SINKS = {
    "logs": re.compile(r"\b(?:console\.(?:log|info|warn|error|debug|trace)|(?:log|logger|LOG|LOGGER|_log)\.(?:info|debug|warn|warning|error|trace|fatal)|(?:info|debug|warn|error|trace)!)\s*\("),
    "http": re.compile(r"\b(?:fetch|axios(?:\.\w+)?|http\.request|https\.request|\.send|\.post|\.put|\.patch|reqwest::\w+(?:::\w+)*|HttpRequest\.newBuilder)\s*\("),
    "print": re.compile(r"\b(?:System\.(?:out|err)\.print\w*|println!|eprintln!|print!|eprint!|process\.stdout\.write)\s*\("),
}


def rules(d) -> list:
    """(name, fields, stays_in, sinks) per declared kind of data."""
    out = []
    for name, spec in sorted(d.data.items()):
        fields, stays = _as_list(spec.get("fields")), _as_list(spec.get("stays_in"))
        sinks = [s for s in (_as_list(spec.get("never_to")) or ["logs", "http", "print"]) if s in SINK_CALLS]
        if fields:
            out.append((name, fields, stays, sinks))
    return out


# ---- the code without comments ------------------------------------------------------------------------------------

def _python_code(text: str) -> str:
    """Python without comments (tokenize knows a `#` inside a string)."""
    try:
        toks = [t for t in tokenize.generate_tokens(io.StringIO(text).readline) if t.type != tokenize.COMMENT]
        return tokenize.untokenize(toks)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return text


def code_of(f: Path) -> str:
    text = f.read_text(encoding="utf-8", errors="replace")
    lang = EXT.get(f.suffix)
    if lang == "python":
        return _python_code(text)
    if lang in ("js", "java", "rust"):
        return strip_comments(text, lang, keep_lines=True)
    if lang == "abap":
        return "\n".join(re.sub(r'".*$', "", l) if not l.lstrip().startswith("*") else "" for l in text.splitlines())
    return text


def _field_rx(fields: list):
    return re.compile(r"(?<![\w$])(" + "|".join(re.escape(f) for f in fields) + r")(?![\w$])")


# ---- outside the boundary -----------------------------------------------------------------------------------------

def _outside_files(d, files: list, stays: list) -> list:
    """The files of isolations that may not hold the data (none when the data names no isolation)."""
    if not stays:
        return []
    return [f for f in files if d.owner_of(f) and not any(d.is_within(d.owner_of(f), s) for s in stays)]


def _first_mention(code: str, rx):
    """(line, field) of the first line that writes a field, else None."""
    for number, line in enumerate(code.splitlines(), 1):
        m = rx.search(line)
        if m:
            return number, m.group(1)
    return None


def outside(d, files: list, root: Path) -> list:
    """(file, line, message) for a field written in a file whose isolation may not hold that data."""
    out = []
    for name, fields, stays, _sinks in rules(d):
        rx = _field_rx(fields)
        for f in _outside_files(d, files, stays):
            hit = _first_mention(code_of(root / f), rx)
            if hit:
                out.append((f, hit[0], f"`{hit[1]}` ({name} data) in `{d.owner_of(f)}`: {name} data stays in {', '.join(stays)}"))
    return out


# ---- sinks: Python by AST, the brace languages by statement -------------------------------------------------------

_CARRIERS = {   # node type -> the name it carries: `x.card_number`, `"card_number"`, `f(card_number=...)`
    ast.Attribute: lambda n: n.attr,
    ast.Constant: lambda n: n.value if isinstance(n.value, str) else "",
    ast.keyword: lambda n: n.arg or "",
}


def _carried(n, fields: set, tainted: dict) -> str:
    """The field one node carries: a name of the field or a local tainted by it, an attribute, a key, a keyword."""
    if isinstance(n, ast.Name):
        return tainted.get(n.id) or (n.id if n.id in fields else "")
    name = _CARRIERS.get(type(n), lambda _n: "")(n)
    return name if name in fields else ""


def _mentions(node, fields: set, tainted: dict) -> str:
    """The field (or the tainted local) an expression carries, else ''."""
    return next((c for n in ast.walk(node) if (c := _carried(n, fields, tainted))), "")


def _sink_kind(call: ast.Call, sinks: list) -> str:
    name = call_name(call)
    for kind in sinks:
        if SINK_CALLS[kind].search(name) and (kind != "logs" or LOG_RECEIVER.search(name + ".") or name.startswith("logging.")):
            return kind
    return ""


SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)


def _taint_assignment(node, fields: set, tainted: dict):
    """Record the locals an assignment fills with a field, or with a local already tainted."""
    if not isinstance(node, (ast.Assign, ast.AnnAssign)) or node.value is None:
        return
    src = _mentions(node.value, fields, tainted)
    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
    if src:
        tainted.update({n.id: src for t in targets for n in ast.walk(t) if isinstance(n, ast.Name)})


def _sink_hit(node, fields: set, tainted: dict, sinks: list):
    """(line, field, sink, call) when a call is a sink and one of its arguments carries a field, else None."""
    kind = _sink_kind(node, sinks) if isinstance(node, ast.Call) else ""
    if not kind:
        return None
    hit = _mentions(ast.Tuple(elts=list(node.args) + [k.value for k in node.keywords], ctx=ast.Load()), fields, tainted)
    return (node.lineno, hit, kind, call_name(node)) if hit else None


def _scope_nodes(scope) -> list:
    """The nodes of one scope: a function's body, or the module's own code, never the body of a function inside it
    (each function is a scope of its own: a local of one never taints another's)."""
    out, todo = [], list(ast.iter_child_nodes(scope))
    while todo:
        node = todo.pop()
        out.append(node)
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            todo += list(ast.iter_child_nodes(node))
    return sorted(out, key=lambda n: (getattr(n, "lineno", 0), getattr(n, "col_offset", 0)))


def _scope_sinks(scope, fields: set, sinks: list) -> list:
    tainted, out = {}, []
    for node in _scope_nodes(scope):
        _taint_assignment(node, fields, tainted)
        hit = _sink_hit(node, fields, tainted, sinks)
        if hit:
            out.append(hit)
    return out


def _python_sinks(text: str, fields: set, sinks: list) -> list:
    """(line, field, sink, call) where a field, directly or through a local it was assigned to, reaches a sink."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    scopes = [n for n in ast.walk(tree) if isinstance(n, SCOPES)]
    return sorted({hit for s in scopes for hit in _scope_sinks(s, fields, sinks)})


def _brace_sinks(code: str, fields: list, sinks: list) -> list:
    rx, out = _field_rx(fields), []
    for i, line in enumerate(code.splitlines(), 1):
        for kind in sinks:
            m = BRACE_SINKS[kind].search(line)
            if m and rx.search(line[m.start():]):
                out.append((i, rx.search(line[m.start():]).group(1), kind, m.group(0).rstrip("( ")))
    return out


def sinks(d, files: list, root: Path) -> list:
    """(file, line, message) for a field that reaches a logger, print or an outbound call."""
    out = []
    for name, fields, _stays, kinds in rules(d):
        for f in files:
            lang = EXT.get(Path(f).suffix)
            text = (root / f).read_text(encoding="utf-8", errors="replace")
            hits = _python_sinks(text, set(fields), kinds) if lang == "python" else _brace_sinks(code_of(root / f), fields, kinds) if lang in ("js", "java", "rust") else []
            out += [(f, line, f"`{field}` ({name} data) reaches {kind}: {call}(...)") for line, field, kind, call in hits]
    return out
