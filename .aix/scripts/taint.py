"""Leaf: taint analysis of Python files. Sources (request attributes, environment, stdin, decorated route
parameters) flow through assignments and loops; a sink reached without a sanitiser is a finding, local calls are
followed one level."""
import ast
from pathlib import Path

from codefiles import ROOT, rel, source_files
from depedges import iter_functions
from securityrules import ACCEPT, ADVICE, SKIP_FILE, MARKER_LINES


REQUEST_ATTRS = {"args", "form", "json", "values", "data", "files", "GET", "POST", "query_params", "path_params",
                 "headers", "cookies", "body", "get_json", "get_data", "stream"}
SOURCE_CALLS = {"input", "os.getenv", "os.environ.get", "sys.stdin.read", "sys.stdin.readline"}
SANITISERS = {"int", "float", "bool", "len", "shlex.quote", "escape", "html.escape", "markupsafe.escape", "bleach.clean",
              "secure_filename", "uuid.UUID", "abs", "round", "re.fullmatch", "ipaddress.ip_address"}
SINKS = {  # dotted call name (suffix match) -> (VUL row, CWE, kind, which args are dangerous)
    "subprocess.run": ("VUL-INJ-002", "CWE-78", "shell command", "shell"), "subprocess.call": ("VUL-INJ-002", "CWE-78", "shell command", "shell"),
    "subprocess.check_output": ("VUL-INJ-002", "CWE-78", "shell command", "shell"), "subprocess.check_call": ("VUL-INJ-002", "CWE-78", "shell command", "shell"),
    "subprocess.Popen": ("VUL-INJ-002", "CWE-78", "shell command", "shell"),
    "os.system": ("VUL-INJ-002", "CWE-78", "shell command", "any"), "os.popen": ("VUL-INJ-002", "CWE-78", "shell command", "any"),
    "eval": ("VUL-INJ-002", "CWE-95", "eval", "any"), "exec": ("VUL-INJ-002", "CWE-95", "exec", "any"),
    ".execute": ("VUL-INJ-001", "CWE-89", "SQL statement", "first"), ".executemany": ("VUL-INJ-001", "CWE-89", "SQL statement", "first"),
    ".raw": ("VUL-INJ-001", "CWE-89", "raw SQL", "first"),
    "open": ("VUL-INJ-002", "CWE-22", "file path", "first"), "send_file": ("VUL-INJ-002", "CWE-22", "file path", "first"),
    "send_from_directory": ("VUL-INJ-002", "CWE-22", "file path", "any"), "os.remove": ("VUL-INJ-002", "CWE-22", "file path", "first"),
    "os.unlink": ("VUL-INJ-002", "CWE-22", "file path", "first"), "shutil.rmtree": ("VUL-INJ-002", "CWE-22", "file path", "first"),
    "shutil.copy": ("VUL-INJ-002", "CWE-22", "file path", "any"), "Path": ("VUL-INJ-002", "CWE-22", "file path", "first"),
    "redirect": ("VUL-WEB-003", "CWE-601", "redirect target", "first"), "RedirectResponse": ("VUL-WEB-003", "CWE-601", "redirect target", "first"),
    "render_template_string": ("VUL-INJ-002", "CWE-1336", "template string", "first"), "Template": ("VUL-INJ-002", "CWE-1336", "template string", "first"),
    "yaml.load": ("VUL-INPUT-002", "CWE-502", "yaml.load", "first"), "pickle.loads": ("VUL-INPUT-002", "CWE-502", "pickle", "first"),
    "pickle.load": ("VUL-INPUT-002", "CWE-502", "pickle", "first"), "marshal.loads": ("VUL-INPUT-002", "CWE-502", "marshal", "first"),
    "requests.get": ("VUL-INPUT-001", "CWE-918", "outbound request URL", "first"), "requests.post": ("VUL-INPUT-001", "CWE-918", "outbound request URL", "first"),
    "urllib.request.urlopen": ("VUL-INPUT-001", "CWE-918", "outbound request URL", "first"), "httpx.get": ("VUL-INPUT-001", "CWE-918", "outbound request URL", "first"),
}

# ---- taint: Python, per file --------------------------------------------------------------------------------------

def dotted(node):
    """'a.b.c' for Name/Attribute chains, '' otherwise."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr); node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    if isinstance(node, ast.Call):
        return dotted(node.func) + "()"
    return ""


def call_name(call: ast.Call) -> str:
    return dotted(call.func)


ENV_BASES = ("sys.argv", "os.environ")
TAINTED_SUBSCRIPTS = (".args", ".form", ".GET", ".POST", ".json")
GETTERS = (".args.get", ".form.get", ".GET.get", ".POST.get", ".headers.get", ".cookies.get", ".query_params.get", ".environ.get")
COMPOUND = (ast.JoinedStr, ast.BinOp, ast.Tuple, ast.List, ast.Set, ast.Dict, ast.IfExp, ast.Await, ast.FormattedValue, ast.BoolOp, ast.Compare)


def _first_source(nodes, tainted) -> str:
    for n in nodes:
        s = is_source(n, tainted)
        if s:
            return s
    return ""


def _attribute_source(node):
    """(description, nodes still to inspect): `request.args` / `os.environ` are sources; else look at the base."""
    base = dotted(node.value)
    if (base.split(".")[-1] == "request" and node.attr in REQUEST_ATTRS) or base in ENV_BASES:
        return f"{base}.{node.attr}", []
    return "", [node.value]


def _subscript_source(node):
    b = dotted(node.value)
    if b in ENV_BASES or b.endswith(TAINTED_SUBSCRIPTS):
        return b + "[...]", []
    return "", [node.value, node.slice]


def _is_sanitiser(name: str) -> bool:
    return name in SANITISERS or name.split(".")[-1] in SANITISERS


def _call_source(node):
    """A sanitiser stops the taint; a known source call is one; else the arguments, then the receiver, are inspected."""
    name = call_name(node)
    if _is_sanitiser(name):
        return "", []
    if name in SOURCE_CALLS or name.endswith((".get_json", ".get_data")) or (name.endswith(".json") and "request" in name) or name.endswith(GETTERS):
        return name + "()", []
    more = list(node.args) + [k.value for k in node.keywords] + ([node.func] if isinstance(node.func, ast.Attribute) else [])
    return "", more


INSPECT = {ast.Attribute: _attribute_source, ast.Subscript: _subscript_source, ast.Call: _call_source}


def _inspect(node, tainted):
    """(description, nodes still to inspect) for one node."""
    if isinstance(node, ast.Name):
        return tainted.get(node.id, ""), []
    if type(node) in INSPECT:
        return INSPECT[type(node)](node)
    return "", (list(ast.iter_child_nodes(node)) if isinstance(node, COMPOUND) else [])


def is_source(node, tainted) -> str:
    """A description if `node` is an input source or carries taint, else ''. A worklist, breadth first, so the
    helpers never call back: each returns what it found and what is left to look at."""
    todo = [node]
    while todo:
        found, more = _inspect(todo.pop(0), tainted)
        if found:
            return found
        todo += more
    return ""


def decorated_params(fn):
    """Parameters of a decorated function (route handler, command, task) are input, except DI defaults."""
    if not fn.decorator_list:
        return []
    out = []
    for a, default in zip(fn.args.args[::-1], (fn.args.defaults[::-1] + [None] * len(fn.args.args))):
        if a.arg in ("self", "cls"):
            continue
        if isinstance(default, ast.Call) and call_name(default) in ("Depends", "Security", "Body", "Header", "Cookie", "Query", "Path", "Form"):
            if call_name(default) in ("Depends", "Security"):
                continue
        out.append(a.arg)
    return out


def _matches_sink(name: str, sink: str) -> bool:
    return name == sink or (sink.startswith(".") and name.endswith(sink)) or name.endswith("." + sink)


def _shell_true(call) -> bool:
    return any(k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True for k in call.keywords)


def _sink_applies(call, kind: str, which: str) -> bool:
    """False for the safe forms: parameterised execute(sql, params) and subprocess without shell=True."""
    if kind == "SQL statement" and len(call.args) > 1:
        return False
    return which != "shell" or _shell_true(call)


def sink_hits(call, tainted):
    """(vul, cwe, kind, source) when a tainted value reaches the sink this call names, else None."""
    name = call_name(call)
    for sink, (vul, cwe, kind, which) in SINKS.items():
        if not _matches_sink(name, sink) or not _sink_applies(call, kind, which):
            continue
        args = call.args if which != "first" else call.args[:1]
        src = _first_source(args + [k.value for k in call.keywords if which == "any"], tainted)
        if src:
            return (vul, cwe, kind, src)
    return None


class _Taint:
    """One function's taint walk: what the caller passed in, what the file's functions are, where findings go."""
    def __init__(self, file, funcs, findings, depth=0, seen=None):
        self.file, self.funcs, self.findings, self.depth, self.seen = file, funcs, findings, depth, seen or set()
        self.lines = file.read_text(encoding="utf-8", errors="replace").splitlines() if depth == 0 else []

    def _accepted(self, lineno: int):
        """The reason after `# aix: accepted VUL-… why` on the sink's line, else None."""
        m = ACCEPT.search(self.lines[lineno - 1]) if lineno <= len(self.lines) else None
        return (m.group(2).strip() or "accepted") if m else None

    def follow(self, fn, params_tainted=None):
        tainted = dict(params_tainted or {})
        for p in decorated_params(fn):
            tainted[p] = f"parameter {p} of {fn.name}"
        guard_resolve = any(isinstance(n, ast.Call) and call_name(n).endswith("is_relative_to") for n in ast.walk(fn))
        for node in ast.walk(fn):
            if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
                self._assignment(node, tainted, guard_resolve)
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                self._loop(node, tainted)
            elif isinstance(node, ast.Call):
                self._call(fn, node, tainted)

    def _assignment(self, node, tainted, guard_resolve):
        value = node.value
        if value is None:
            return
        src = is_source(value, tainted)
        if isinstance(value, ast.Call) and call_name(value).endswith(".resolve") and guard_resolve:
            src = ""
        for t in (node.targets if isinstance(node, ast.Assign) else [node.target]):
            for n in ast.walk(t):
                if isinstance(n, ast.Name):
                    if src:
                        tainted[n.id] = f"{n.id} = ... from {src} (line {node.lineno})"
                    else:
                        tainted.pop(n.id, None)

    def _loop(self, node, tainted):
        src = is_source(node.iter, tainted)
        for n in ast.walk(node.target):
            if isinstance(n, ast.Name) and src:
                tainted[n.id] = f"{n.id} iterates {src} (line {node.lineno})"

    def _call(self, fn, node, tainted):
        hit = sink_hits(node, tainted)
        if hit:
            vul, cwe, kind, src = hit
            self.findings.append((vul, cwe, f"input reaches {kind}", rel(self.file), node.lineno, f"{call_name(node)}(...) <- {src}", ADVICE[cwe], self._accepted(node.lineno)))
        name = call_name(node)
        if self.depth < 1 and name in self.funcs and name not in self.seen:
            passed = self._passed_taint(fn, node, self.funcs[name], tainted)
            if passed:
                inner = _Taint(self.file, self.funcs, self.findings, self.depth + 1, self.seen | {name})
                inner.lines = self.lines
                inner.follow(self.funcs[name], passed)

    @staticmethod
    def _passed_taint(fn, node, callee, tainted) -> dict:
        """The callee's parameters that receive tainted arguments, by position and by keyword."""
        pt = {}
        for i, a in enumerate(node.args):
            s = is_source(a, tainted)
            if s and i < len(callee.args.args):
                pt[callee.args.args[i].arg] = f"argument from {fn.name} line {node.lineno}: {s}"
        for k in node.keywords:
            s = is_source(k.value, tainted)
            if s and k.arg:
                pt[k.arg] = f"argument from {fn.name} line {node.lineno}: {s}"
        return pt


def taint_function(fn, file, funcs, findings):
    """Walk statements in order, propagate taint through assignments, report sinks, follow local calls one level."""
    _Taint(file, funcs, findings).follow(fn)


def taint_file(file: Path, findings):
    try:
        tree = ast.parse(file.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return
    if any(SKIP_FILE.search(l) for l in file.read_text(encoding="utf-8", errors="replace").splitlines()[:MARKER_LINES]):
        return
    funcs = {fn.name: fn for cls, fn in iter_functions(tree) if not cls}
    for cls, fn in iter_functions(tree):
        taint_function(fn, file, funcs, findings)


def taint(paths):
    findings = []
    for p in paths:
        base = (ROOT / p) if not Path(p).is_absolute() else Path(p)
        for f in ([base] if base.is_file() else source_files([str(base)])):
            if f.suffix == ".py":
                taint_file(f, findings)
    seen, out = set(), []
    for fx in findings:
        key = (fx[0], fx[3], fx[4])
        if key not in seen:
            seen.add(key); out.append(fx)
    return out
