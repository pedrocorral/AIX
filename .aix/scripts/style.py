#!/usr/bin/env python3
"""aix code style — readability of functions and files, with specific, line-numbered feedback.

Per function: lines, cognitive complexity (Campbell / SonarSource 2017), cyclomatic complexity (McCabe 1976),
nesting depth, parameters, naming, docstring, magic numbers. Per file: length. Thresholds live in .aix/config.yaml
(`style:` block) with defaults from the literature (.aix/meta-docs/conventions/readability.md).
Python is measured exactly through the parser; JS/TS, Rust and Java through tokens and braces (approximate).

Targets: a directory, a file (extension optional), or one function: path:func, path/func, path::Class.method."""
import ast, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import ROOT, CODE_ROOTS, EXT, FUNC_HEAD, KEYWORDS, TOKEN, brace_block, iter_functions, rel, source_files

DEFAULTS = dict(max_lines=60, max_cognitive=15, max_cyclomatic=10, max_nesting=4, max_params=5, max_file_lines=400)
PLAIN_NUMBERS = {0, 1, 2, -1, 10, 100, 1000, 0.5, 1.0, 0.0, 2.0} | {200, 201, 202, 204, 301, 302, 304, 400, 401, 403, 404, 405, 409, 410, 422, 429, 500, 502, 503, 504}
TEST_LINES_FACTOR = 2      # a test is a sequential story: twice the line limit, no magic-number or docstring advice
JSX = re.compile(r"</|/>")
LOOP_VARS = {"i", "j", "k", "n", "x", "y", "z", "_", "e", "f", "p", "m", "t"}
CASE = {"python": ("snake", re.compile(r"^_{0,2}[a-z][a-z0-9_]*$")), "rust": ("snake", re.compile(r"^[a-z][a-z0-9_]*$")),
        "js": ("camel", re.compile(r"^[a-z$_][A-Za-z0-9$_]*$")), "java": ("camel", re.compile(r"^[a-z][A-Za-z0-9]*$"))}


def thresholds():
    """.aix/config.yaml `style:` block overrides DEFAULTS; missing keys keep the default."""
    out = dict(DEFAULTS)
    fy = ROOT / ".aix" / "config.yaml"
    if fy.exists():
        block = re.search(r"^style:\s*\n((?:[ \t]+\S.*\n?)+)", fy.read_text(encoding="utf-8"), re.M)
        if block:
            for k, v in re.findall(r"^\s+(\w+):\s*([\d.]+)", block.group(1), re.M):
                if k in out:
                    out[k] = float(v) if "." in v else int(v)
    return out


# ---- Python metrics -------------------------------------------------------------------------------------------

BRANCH = (ast.If, ast.For, ast.While, ast.AsyncFor, ast.ExceptHandler, ast.IfExp, ast.With, ast.AsyncWith, ast.Try)
NESTING = (ast.If, ast.For, ast.While, ast.AsyncFor, ast.ExceptHandler, ast.With, ast.AsyncWith, ast.Try, ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)


def cyclomatic_py(fn) -> int:
    n = 1
    for node in ast.walk(fn):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.AsyncFor, ast.ExceptHandler, ast.IfExp)):
            n += 1
        elif isinstance(node, ast.BoolOp):
            n += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            n += 1 + len(node.ifs)
        elif isinstance(node, ast.Match):
            n += len(node.cases)
    return n


def cognitive_py(fn):
    """SonarSource cognitive complexity: +1 per break in linear flow (if/elif/else, loops, except, ternary,
    boolean-operator sequences, recursion), +nesting level for the nested ones, elif/else without nesting penalty.
    Returns (total, [(line, increment, reason)])."""
    total, items = 0, []

    def add(node, inc, reason):
        nonlocal total
        total += inc; items.append((getattr(node, "lineno", fn.lineno), inc, reason))

    def visit(node, depth):
        if isinstance(node, ast.If):
            add(node, 1 + depth, f"if (+1, nesting +{depth})" if depth else "if (+1)")
            for child in node.body:
                visit(child, depth + 1)
            if node.orelse:
                if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                    add(node.orelse[0], 1, "elif (+1)")
                    _visit_elif(node.orelse[0], depth)
                else:
                    add(node.orelse[0], 1, "else (+1)")
                    for child in node.orelse:
                        visit(child, depth + 1)
            visit(node.test, depth)
            return
        if isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
            add(node, 1 + depth, f"loop (+1, nesting +{depth})" if depth else "loop (+1)")
            for child in node.body + node.orelse:
                visit(child, depth + 1)
            return
        if isinstance(node, ast.Try):
            for child in node.body + node.orelse + node.finalbody:
                visit(child, depth)
            for h in node.handlers:
                add(h, 1 + depth, f"except (+1, nesting +{depth})" if depth else "except (+1)")
                for child in h.body:
                    visit(child, depth + 1)
            return
        if isinstance(node, ast.IfExp):
            add(node, 1 + depth, "ternary (+1)")
            for child in ast.iter_child_nodes(node):
                visit(child, depth + 1)
            return
        if isinstance(node, ast.BoolOp):
            add(node, 1, "boolean operator sequence (+1)")
            for child in node.values:
                visit(child, depth)
            return
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and node is not fn:
            for child in ast.iter_child_nodes(node):
                visit(child, depth + 1)
            return
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == fn.name:
            add(node, 1, "recursion (+1)")
        for child in ast.iter_child_nodes(node):
            visit(child, depth)

    def _visit_elif(node, depth):
        for child in node.body:
            visit(child, depth + 1)
        visit(node.test, depth)
        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                add(node.orelse[0], 1, "elif (+1)"); _visit_elif(node.orelse[0], depth)
            else:
                add(node.orelse[0], 1, "else (+1)")
                for child in node.orelse:
                    visit(child, depth + 1)

    for stmt in fn.body:
        visit(stmt, 0)
    return total, items


def nesting_py(fn):
    """(max depth, (first line, last line) of the deepest block) — the block to extract."""
    best = (0, (fn.lineno, fn.lineno))

    def visit(node, depth):
        nonlocal best
        if isinstance(node, NESTING) and node is not fn:
            depth += 1
            if depth > best[0]:
                best = (depth, (node.lineno, getattr(node, "end_lineno", node.lineno)))
        for child in ast.iter_child_nodes(node):
            visit(child, depth)
    visit(fn, 0)
    return best


def names_py(fn):
    """Single-letter names assigned outside loops/comprehensions (loop counters are fine)."""
    loop_names = set()
    for node in ast.walk(fn):
        if isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
            loop_names |= {n.id for n in ast.walk(node.target) if isinstance(n, ast.Name)}
    out = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store) and len(node.id) == 1 and node.id not in loop_names and node.id != "_":
            out.append((node.lineno, node.id))
    return sorted(set(out))


def magic_py(fn):
    out = []
    for node in ast.walk(fn):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool) and node.value not in PLAIN_NUMBERS:
            out.append((node.lineno, node.value))
    return sorted(set(out))


def is_test(file: Path, name: str) -> bool:
    p = file.resolve()
    return "tests" in p.parts or "test" in p.parts or "__tests__" in p.parts or p.name.startswith("test_") \
        or p.name.endswith(("_test.py", ".test.ts", ".test.tsx", ".test.js", ".spec.ts", ".spec.js")) or name.startswith("test")


def analyse_py(file: Path, cls, fn, lang="python"):
    params = [a.arg for a in fn.args.args + fn.args.kwonlyargs if a.arg not in ("self", "cls")]
    cog, cog_items = cognitive_py(fn)
    depth, block = nesting_py(fn)
    doc = ast.get_docstring(fn) is not None
    return dict(name=f"{cls + '.' if cls else ''}{fn.name}", file=rel(file), line=fn.lineno, lang=lang,
                lines=(fn.end_lineno or fn.lineno) - fn.lineno + 1, params=len(params), cyclomatic=cyclomatic_py(fn),
                cognitive=cog, cognitive_items=cog_items, nesting=depth, deepest=block, docstring=doc,
                public=not fn.name.startswith("_"), short_names=names_py(fn), magic=magic_py(fn), fname=fn.name, node=fn, cls=cls,
                test=is_test(file, fn.name), decorated=bool(fn.decorator_list), jsx=False)


# ---- other languages: tokens and braces --------------------------------------------------------------------------

def analyse_tokens(file: Path, name: str, header_end: int, text: str, lang: str):
    start_line = text.count("\n", 0, header_end) + 1
    body = brace_block(text, header_end)
    lines = body.count("\n") + 1
    head = text[text.rfind("\n", 0, header_end) + 1:header_end]
    params_txt = re.search(r"\(([^)]*)\)", head)
    params = [p for p in (params_txt.group(1).split(",") if params_txt else []) if p.strip() and p.strip() not in ("self", "&self", "&mut self", "this")]
    cleaned = re.sub(r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", " ", body, flags=re.S)
    depth = cur = 0
    cog = cyc = 1, 1
    cog, cyc, cog_items, deepest, deepest_line = 0, 1, [], (start_line, start_line), start_line
    for m in re.finditer(r"\{|\}|\b(if|for|while|switch|catch|match|loop|else)\b|&&|\|\||\?", cleaned):
        tok = m.group(0)
        line = start_line + cleaned.count("\n", 0, m.start())
        if tok == "{":
            cur += 1
            if cur > depth:
                depth, deepest_line = cur, line
        elif tok == "}":
            cur -= 1
        elif tok in ("if", "for", "while", "switch", "catch", "match", "loop"):
            cyc += 1; inc = 1 + max(cur - 1, 0); cog += inc
            cog_items.append((line, inc, f"{tok} (+1, nesting +{max(cur - 1, 0)})" if cur > 1 else f"{tok} (+1)"))
        elif tok == "else":
            cog += 1; cog_items.append((line, 1, "else (+1)"))
        elif tok in ("&&", "||"):
            cyc += 1; cog += 1; cog_items.append((line, 1, "boolean operator (+1)"))
        elif tok == "?":
            cyc += 1; cog += 1; cog_items.append((line, 1, "ternary (+1)"))
    before = text[max(0, text.rfind("\n", 0, text.rfind("\n", 0, header_end))):header_end]
    doc = "///" in before or "/**" in before or "*/" in before or "//" in before
    magic = sorted({(start_line + cleaned.count("\n", 0, m.start()), float(m.group(0))) for m in re.finditer(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", cleaned)
                    if float(m.group(0)) not in PLAIN_NUMBERS})
    short = sorted({(start_line + cleaned.count("\n", 0, m.start()), m.group(1)) for m in re.finditer(r"\b(?:let|const|var|mut)\s+([a-zA-Z])\b", cleaned) if m.group(1) not in LOOP_VARS})
    return dict(name=name, file=rel(file), line=start_line, lang=lang, lines=lines, params=len(params), cyclomatic=cyc,
                cognitive=cog, cognitive_items=cog_items, nesting=max(depth - 1, 0), deepest=(deepest_line, deepest_line),
                docstring=doc, public=not name.startswith("_"), short_names=short, magic=magic, fname=name, src=body,
                test=is_test(file, name), decorated=bool(re.search(r"@\w+\s*(?:\([^)]*\))?\s*$", before)), jsx=bool(JSX.search(body)) or file.suffix in (".jsx", ".tsx"))


# ---- targets ----------------------------------------------------------------------------------------------------

def resolve_file(spec: str):
    p = ROOT / spec if not Path(spec).is_absolute() else Path(spec)
    if p.is_file():
        return p
    for e in EXT:
        if p.with_suffix(e).is_file():
            return p.with_suffix(e)
    return None


def parse_target(spec: str):
    """-> ('dir', Path) | ('file', Path) | ('func', Path, name) | None. Accepts path:func, path::Class.m, path/func."""
    for sep in ("::", ":"):  # explicit function separators first: "a.py::m" must not be read as a file
        if sep in spec:
            path, name = spec.rsplit(sep, 1)
            f = resolve_file(path)
            if f and name:
                return ("func", f, name)
    p = ROOT / spec if not Path(spec).is_absolute() else Path(spec)
    if p.is_dir():
        return ("dir", p)
    f = resolve_file(spec)
    if f:
        return ("file", f)
    if "/" in spec:
        path, name = spec.rsplit("/", 1)
        f = resolve_file(path)
        if f and name:
            return ("func", f, name)
    return None


def functions_in(file: Path):
    lang = EXT.get(file.suffix)
    if not lang:
        return []
    text = file.read_text(encoding="utf-8", errors="replace")
    if lang == "python":
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return []
        return [analyse_py(file, cls, fn) for cls, fn in iter_functions(tree)]
    out = []
    for m in FUNC_HEAD[lang].finditer(text):
        name = next((g for g in m.groups() if g), None)
        if name and name not in KEYWORDS:
            out.append(analyse_tokens(file, name, m.end() - 1, text, lang))
    return out


def file_lines(file: Path) -> int:
    return file.read_text(encoding="utf-8", errors="replace").count("\n") + 1


# ---- modernisation: only what the detected runtime allows ---------------------------------------------------------

def _py_at_least(rt, major, minor):
    v = rt.get("python", (None,))[0]
    return v is not None and v >= (major, minor)


def _typing_names(node):
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)} | {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}


def modern_py(fx, rt):
    fn, out = fx["node"], []
    if _py_at_least(rt, 3, 10):
        for node in ast.walk(fn):
            if isinstance(node, ast.If) and _elif_ladder_on_one_name(node) >= 3:
                out.append((node.lineno, "if/elif ladder comparing one value", "a `match` statement (Python 3.10+) reads as a table and cuts nesting"))
                break
        ann = [a for a in fn.args.args + fn.args.kwonlyargs if a.annotation] + ([fn] if fn.returns else [])
        names = set()
        for a in ann:
            names |= _typing_names(a.annotation if a is not fn else fn.returns)
        if "Optional" in names or "Union" in names:
            out.append((fn.lineno, "`Optional[...]` / `Union[...]` in the signature", "write `X | None` and `A | B` (Python 3.10+)"))
        if names & {"List", "Dict", "Set", "Tuple", "FrozenSet", "Type"}:
            out.append((fn.lineno, "`typing.List/Dict/Set/Tuple` in the signature", "use the builtins `list[...]`, `dict[...]` (Python 3.9+)"))
    if _py_at_least(rt, 3, 7) and fx["fname"] == "__init__" and fx["cls"] and fn.body and all(
            isinstance(s, ast.Assign) and len(s.targets) == 1 and isinstance(s.targets[0], ast.Attribute)
            and isinstance(s.value, ast.Name) for s in fn.body):
        out.append((fn.lineno, "`__init__` that only assigns its parameters", f"`@dataclass` on `{fx['cls']}` removes it (Python 3.7+)"))
    for node in ast.walk(fn):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute) and isinstance(node.value.value, ast.Name) \
                and node.value.value.id == "os" and node.value.attr == "path":
            out.append((node.lineno, f"`os.path.{node.attr}`", "`pathlib.Path` reads as objects, not string plumbing"))
            break
    if _py_at_least(rt, 3, 11):
        for node in ast.walk(fn):
            if isinstance(node, ast.Import) and any(a.name in ("toml", "tomli") for a in node.names):
                out.append((node.lineno, "`import toml/tomli`", "`tomllib` is in the standard library (Python 3.11+)"))
    return out


def _elif_ladder_on_one_name(node) -> int:
    """Length of an if/elif chain whose every test is `NAME == constant` on the same NAME (else 0)."""
    name, count = None, 0
    while isinstance(node, ast.If):
        t = node.test
        if not (isinstance(t, ast.Compare) and len(t.ops) == 1 and isinstance(t.ops[0], ast.Eq)
                and isinstance(t.left, ast.Name) and isinstance(t.comparators[0], ast.Constant)):
            return 0
        if name is None:
            name = t.left.id
        elif t.left.id != name:
            return 0
        count += 1
        node = node.orelse[0] if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If) else None
    return count


def modern_tokens(fx, rt):
    src, lang, out = fx.get("src", ""), fx["lang"], []
    base = fx["line"]
    line_of = lambda m: base + src.count("\n", 0, m.start())
    if lang == "js":
        es = rt.get("js", (None,))[0]
        if es and es[0] >= 2020:
            m = re.search(r"\b([A-Za-z_$][\w$.]*)\s*&&\s*\1\.", src)
            if m:
                out.append((line_of(m), f"`{m.group(1)} && {m.group(1)}.…`", "optional chaining `?.` (ES2020)"))
            m = re.search(r"\b([A-Za-z_$][\w$.]*)\s*!==?\s*(?:undefined|null)\s*\?\s*\1\s*:", src)
            if m:
                out.append((line_of(m), f"`{m.group(1)} !== undefined ? {m.group(1)} : …`", "nullish coalescing `??` (ES2020)"))
        if es and es[0] >= 2015 and re.search(r"\bvar\s+\w", src):
            out.append((line_of(re.search(r"\bvar\s+\w", src)), "`var`", "`const`/`let` have block scope (ES2015)"))
    elif lang == "rust":
        v = rt.get("rust", (None,))[0]
        if v and v >= (1, 65):
            m = re.search(r"match\s+[^{]+\{\s*(?:Some|Ok)\((\w+)\)\s*=>\s*\1\s*,\s*(?:None|Err\([^)]*\))\s*=>\s*(?:return|continue|break)", src)
            if m:
                out.append((line_of(m), "match that only unwraps or returns", "`let … else` (Rust 1.65+)"))
    elif lang == "java":
        v = rt.get("java", (None,))[0]
        if v and v[0] >= 14 and re.search(r"\bswitch\s*\(", src) and "->" not in src and re.search(r"\bbreak\s*;", src):
            out.append((line_of(re.search(r"\bswitch\s*\(", src)), "switch with `break`s", "switch expression with `->` (Java 14+)"))
    return out


def modernisations(fx, rt):
    return modern_py(fx, rt) if fx["lang"] == "python" else modern_tokens(fx, rt)


# ---- findings ---------------------------------------------------------------------------------------------------

def limit(fx, th, key):
    """The limit that applies to THIS function: tests get twice the lines; decorated functions (routes, commands,
    fixtures: the framework maps their parameters) have no parameter limit."""
    if key == "lines" and fx["test"]:
        return th["max_lines"] * TEST_LINES_FACTOR
    if key == "params" and fx["decorated"]:
        return 10 ** 6
    return th["max_" + key]


def findings(fx, th):
    """(severity, line, message, advice) — every one specific to this function."""
    out = []
    if fx["lines"] > limit(fx, th, "lines"):
        a, b = fx["deepest"]
        out.append(("over", fx["line"], f"{fx['lines']} lines (limit {limit(fx, th, 'lines')})",
                    f"split: one job per function; the deepest block is lines {a}-{b}, extract it into a named function"))
    if fx["cognitive"] > th["max_cognitive"]:
        worst = sorted(fx["cognitive_items"], key=lambda x: -x[1])[:3]
        where = "; ".join(f"line {l}: {r}" for l, _, r in worst)
        out.append(("over", fx["line"], f"cognitive complexity {fx['cognitive']} (limit {th['max_cognitive']})",
                    f"flatten: guard clauses and early returns, extract nested loops/conditions. Biggest costs: {where}"))
    if fx["cyclomatic"] > th["max_cyclomatic"]:
        out.append(("over", fx["line"], f"cyclomatic complexity {fx['cyclomatic']} (limit {th['max_cyclomatic']})",
                    "too many paths to test: split by case, or replace branch ladders with a lookup table / polymorphism"))
    if fx["nesting"] > th["max_nesting"]:
        a, b = fx["deepest"]
        out.append(("over", a, f"nesting depth {fx['nesting']} (limit {th['max_nesting']}) at lines {a}-{b}",
                    "invert the condition and return early, or extract the inner block into a function"))
    if fx["params"] > limit(fx, th, "params"):
        out.append(("over", fx["line"], f"{fx['params']} parameters (limit {th['max_params']})",
                    "group related parameters into one object (dataclass/struct/options), or split the function"))
    case, rx = CASE[fx["lang"]]
    component = fx["lang"] == "js" and fx["jsx"] and re.match(r"^[A-Z][A-Za-z0-9]*$", fx["fname"])  # React: PascalCase is required
    if not rx.match(fx["fname"]) and not component and not (fx["fname"].startswith("__") and fx["fname"].endswith("__")):
        out.append(("name", fx["line"], f"name `{fx['fname']}` is not {case}_case" if case == "snake" else f"name `{fx['fname']}` is not camelCase",
                    "follow the language convention; a name that looks wrong slows every reader"))
    for line, name in fx["short_names"]:
        out.append(("name", line, f"single-letter name `{name}`", "say what it holds: `count`, `path`, `user`; one-letter names are for loop counters and maths"))
    if fx["public"] and not fx["docstring"] and fx["lines"] >= 6 and not fx["test"]:
        out.append(("doc", fx["line"], "public function without a docstring / doc comment", "one line: what it does and when to call it"))
    for line, value in ([] if fx["test"] else fx["magic"][:5]):
        v = int(value) if float(value).is_integer() else value
        out.append(("magic", line, f"magic number {v}", "name it: a constant tells the reader what the value means"))
    return out


def score(fx, th):
    """How far over the limits, summed; 0 = all metrics inside."""
    return sum(max(0.0, fx[k] / limit(fx, th, k) - 1) for k in ("lines", "cognitive", "cyclomatic", "nesting", "params"))


# ---- rendering --------------------------------------------------------------------------------------------------

def card(fx, th, rt=None):
    lines = [f"{fx['file']}:{fx['name']}  (line {fx['line']}, {fx['lang']})", ""]
    for k, label in (("lines", "lines"), ("cognitive", "cognitive complexity"), ("cyclomatic", "cyclomatic complexity"), ("nesting", "nesting depth"), ("params", "parameters")):
        v, lim = fx[k], limit(fx, th, k)
        note = "  (test: doubled)" if k == "lines" and fx["test"] else "  (decorated: framework-mapped, no limit)" if k == "params" and fx["decorated"] else ""
        lines.append(f"  {label:22s} {v:>4}   limit {str(lim) if lim < 10 ** 6 else '-':<4}  {'OVER' if v > lim else 'ok'}{note}")
    lines.append(f"  {'docstring':22s} {'yes' if fx['docstring'] else 'no':>4}")
    fs = findings(fx, th)
    lines.append("")
    if not fs:
        lines.append("  no findings")
    for sev, line, msg, advice in fs:
        lines.append(f"  line {line:<5} {msg}\n             -> {advice}")
    for line, what, advice in (modernisations(fx, rt) if rt else []):
        lines.append(f"  line {line:<5} modernise: {what}\n             -> {advice}")
    return "\n".join(lines)


def runtime_header(rt, langs):
    return "  runtime: " + "; ".join(f"{rt[l][1]} ({rt[l][2]})" for l in ("python", "js", "rust", "java") if l in langs and l in rt)


def table(fxs, th, files, max_rows=30, rt=None):
    over = [fx for fx in fxs if score(fx, th) > 0 or findings(fx, th)]
    over.sort(key=lambda fx: (-score(fx, th), -len(findings(fx, th))))
    counts = {k: sum(1 for fx in fxs if fx[k] > limit(fx, th, k)) for k in ("lines", "cognitive", "cyclomatic", "nesting", "params")}
    long_files = [(rel(f), n) for f, n in files if n > th["max_file_lines"]]
    n_over = sum(1 for fx in fxs if score(fx, th) > 0)
    lines = [f"  functions analysed {len(fxs)}; over a limit {n_over} (" + ", ".join(f"{k} {v}" for k, v in counts.items())
             + f"); with any finding {len(over)}; files over {th['max_file_lines']} lines: {len(long_files)}", ""]
    if over:
        lines.append(f"  {'FUNCTION':60s} {'lines':>5} {'cogn':>5} {'cycl':>5} {'nest':>5} {'prm':>4}  findings")
    for fx in over[:max_rows]:
        fs = findings(fx, th)
        tag = lambda k: (str(fx[k]) + ("*" if fx[k] > limit(fx, th, k) else " "))
        label = fx['file'] + ':' + fx['name']
        label = label if len(label) <= 60 else "…" + label[-59:]  # keep the function name, cut the path
        lines.append(f"  {label:60s} {tag('lines'):>6}{tag('cognitive'):>6}{tag('cyclomatic'):>6}{tag('nesting'):>6}{tag('params'):>5}  " + "; ".join(m for _, _, m, _ in fs[:2]))
    if len(over) > max_rows:
        lines.append(f"  ... {len(over) - max_rows} more; narrow the target or use --all")
    for f, n in long_files[:10]:
        lines.append(f"  FILE  {f}: {n} lines (limit {th['max_file_lines']})  -> split by responsibility")
    mods = [(fx, m) for fx in fxs for m in (modernisations(fx, rt) if rt else [])]
    if mods:
        lines.append(f"  modernise ({len(mods)}, advice for the detected runtime):")
        for fx, (line, what, advice) in mods[:15]:
            lines.append(f"    {fx['file']}:{fx['name']} line {line}: {what} -> {advice}")
        if len(mods) > 15:
            lines.append(f"    ... {len(mods) - 15} more")
    lines.append("  * = over its limit (gated). Names, docstrings and magic numbers are advice.  Details: aix code style FILE:FUNCTION")
    lines.append("  fix with: OVER -> skill refactor-readability (one metric per change); modernise -> refactor-modernise")
    return "\n".join(lines), n_over + len(long_files)


# ---- self-test --------------------------------------------------------------------------------------------------

SELFTEST_SRC = '''
def simple(a, b):
    return a + b

def sonar_example(x):
    if x > 0:                # +1
        for i in range(x):   # +2 (nesting 1)
            if i % 2:        # +3 (nesting 2)
                pass
    elif x < 0:              # +1
        pass
    else:                    # +1
        pass
    return x and x > 1       # +1 boolean sequence

def ladder(cmd):
    if cmd == "start":
        return 1
    elif cmd == "stop":
        return 2
    elif cmd == "status":
        return 3

def test_many_asserts(client):
    r = client.get("/x")
    assert r.status_code == 200
    assert r.json()["a"] == 1
    assert r.json()["b"] == 2
    assert r.json()["c"] == 3

def deep(a):
    if a:
        if a:
            if a:
                if a:
                    if a:
                        return 86400
'''


def selftest():
    tree = ast.parse(SELFTEST_SRC)
    fxs = {fn.name: analyse_py(Path("selftest.py"), cls, fn) for cls, fn in iter_functions(tree)}
    checks = [("simple cognitive", fxs["simple"]["cognitive"], 0), ("simple cyclomatic", fxs["simple"]["cyclomatic"], 1),
              ("sonar example cognitive", fxs["sonar_example"]["cognitive"], 9), ("sonar example cyclomatic", fxs["sonar_example"]["cyclomatic"], 6),
              ("deep nesting", fxs["deep"]["nesting"], 5), ("deep magic number", len(fxs["deep"]["magic"]), 1),
              ("simple params", fxs["simple"]["params"], 2),
              ("asserts do not add cyclomatic", fxs["test_many_asserts"]["cyclomatic"], 1),
              ("test: 200 is not magic, no magic advice", len([f for f in findings(fxs["test_many_asserts"], DEFAULTS) if f[0] == "magic"]), 0),
              ("ladder -> match under 3.10", len(modern_py(fxs["ladder"], {"python": ((3, 10), "", "")})), 1),
              ("ladder silent under 3.8", len(modern_py(fxs["ladder"], {"python": ((3, 8), "", "")})), 0)]
    failed = 0
    for name, got, want in checks:
        ok = got == want; failed += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: {got} (expected {want})")
    print("selftest: " + ("all passed" if not failed else f"{failed} FAILED"))
    sys.exit(1 if failed else 0)


# ---- main -------------------------------------------------------------------------------------------------------

USAGE = "usage: aix code style [TARGET...] [--all] [--gate] [--report] [--selftest]   TARGET = dir | file[.ext] | file:func | file::Class.method"


def main(args):
    if "--selftest" in args:
        return selftest()
    gate, report, show_all = "--gate" in args, "--report" in args, "--all" in args
    specs = [a for a in args if not a.startswith("--")] or CODE_ROOTS
    th = thresholds()
    import runtime
    rt = runtime.detect(ROOT)
    fxs, files, cards = [], [], []
    for spec in specs:
        t = parse_target(spec)
        if t is None:
            if spec in CODE_ROOTS:
                continue
            sys.exit(f"aix code style: '{spec}' is not a folder, file or file:function in this project")
        if t[0] == "dir":
            for f in source_files([str(t[1])]):
                fxs += functions_in(f); files.append((f, file_lines(f)))
        elif t[0] == "file":
            fxs += functions_in(t[1]); files.append((t[1], file_lines(t[1])))
        else:
            hits = [fx for fx in functions_in(t[1]) if fx["name"] == t[2] or fx["name"].endswith("." + t[2]) or fx["fname"] == t[2]]
            if not hits:
                sys.exit(f"aix code style: no function '{t[2]}' in {rel(t[1])}")
            cards += hits
    langs = {fx["lang"] for fx in fxs + cards}
    if cards and not fxs:
        print("\n\n".join(card(fx, th, rt) for fx in cards))
        print("\n" + runtime_header(rt, langs))
        n = sum(1 for fx in cards if score(fx, th) > 0)
    else:
        text, n = table(fxs + cards, th, files, max_rows=10**6 if show_all else 30, rt=rt)
        text = runtime_header(rt, langs) + "\n" + text
        print(f"Code style — {', '.join(specs)}\n\n" + text)
        if report:
            out = ROOT / "docs" / "tests" / "code-style.md"
            out.write_text("# Code style (generated — do not edit)\n\n```\n" + text + "\n```\n", encoding="utf-8")
            print(f"\n  wrote {out.relative_to(ROOT)}")
    if gate and n:
        sys.exit(f"GATE FAILED: {n} function(s)/file(s) over a limit")
    if gate:
        print("GATE PASSED")


if __name__ == "__main__":
    main(sys.argv[1:])
