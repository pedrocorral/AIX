"""Leaf: the readability numbers of one function. Cyclomatic (McCabe) and cognitive (SonarSource) complexity,
nesting depth, parameter count, single-letter names and magic numbers, for Python by AST and for JS/TS, Rust and
Java by tokens and braces; plus the targets (`dir`, `file`, `file:func`) and the per-file function list."""
import ast, re
from pathlib import Path

from codefiles import ROOT, EXT, rel
from clones import FUNC_HEAD, KEYWORDS, brace_block
from depedges import iter_functions


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


BRANCH_NODES = (ast.If, ast.For, ast.While, ast.AsyncFor, ast.ExceptHandler, ast.IfExp)


def _branches(node) -> int:
    """How many decision points one node adds to McCabe's count."""
    if isinstance(node, BRANCH_NODES):
        return 1
    if isinstance(node, ast.BoolOp):
        return len(node.values) - 1
    if isinstance(node, ast.comprehension):
        return 1 + len(node.ifs)
    return len(node.cases) if isinstance(node, ast.Match) else 0


def cyclomatic_py(fn) -> int:
    return 1 + sum(_branches(node) for node in ast.walk(fn))


class _Cognitive:
    """SonarSource cognitive complexity walk: +1 per break in linear flow, +nesting for the nested ones,
    elif/else without nesting penalty, +1 per boolean-operator sequence and per recursion."""
    def __init__(self, fn):
        self.fn, self.total, self.items = fn, 0, []

    def add(self, node, inc, reason):
        self.total += inc; self.items.append((getattr(node, "lineno", self.fn.lineno), inc, reason))

    def visit(self, node, depth):
        """Dispatch one node: statements that break the flow, expressions that cost, nested functions, the rest."""
        handler = self._handler(node)
        if handler:
            return handler(node, depth)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and node is not self.fn:
            return self._children(node, depth + 1)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == self.fn.name:
            self.add(node, 1, "recursion (+1)")
        self._children(node, depth)

    def _handler(self, node):
        if isinstance(node, ast.If):
            return self._if
        if isinstance(node, (ast.For, ast.While, ast.AsyncFor)):
            return self._loop
        return {ast.Try: self._try, ast.IfExp: self._ternary, ast.BoolOp: self._bool}.get(type(node))

    def _ternary(self, node, depth):
        self.add(node, 1 + depth, "ternary (+1)")
        self._children(node, depth + 1)

    def _bool(self, node, depth):
        self.add(node, 1, "boolean operator sequence (+1)")
        self._each(node.values, depth)

    def _each(self, nodes, depth):
        for child in nodes:
            self.visit(child, depth)

    def _children(self, node, depth):
        self._each(ast.iter_child_nodes(node), depth)

    def _if(self, node, depth, is_elif=False):
        if not is_elif:
            self.add(node, 1 + depth, f"if (+1, nesting +{depth})" if depth else "if (+1)")
        self._each(node.body, depth + 1)
        self.visit(node.test, depth)
        if not node.orelse:
            return
        if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
            self.add(node.orelse[0], 1, "elif (+1)")
            self._if(node.orelse[0], depth, is_elif=True)
        else:
            self.add(node.orelse[0], 1, "else (+1)")
            self._each(node.orelse, depth + 1)

    def _loop(self, node, depth):
        self.add(node, 1 + depth, f"loop (+1, nesting +{depth})" if depth else "loop (+1)")
        self._each(node.body + node.orelse, depth + 1)

    def _try(self, node, depth):
        self._each(node.body + node.orelse + node.finalbody, depth)
        for h in node.handlers:
            self.add(h, 1 + depth, f"except (+1, nesting +{depth})" if depth else "except (+1)")
            self._each(h.body, depth + 1)


def cognitive_py(fn):
    """SonarSource cognitive complexity: +1 per break in linear flow (if/elif/else, loops, except, ternary,
    boolean-operator sequences, recursion), +nesting level for the nested ones, elif/else without nesting penalty.
    Returns (total, [(line, increment, reason)])."""
    c = _Cognitive(fn)
    c._each(fn.body, 0)
    return c.total, c.items


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


def _loop_names(fn) -> set:
    out = set()
    for node in ast.walk(fn):
        if isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
            out |= {n.id for n in ast.walk(node.target) if isinstance(n, ast.Name)}
    return out


def names_py(fn):
    """Single-letter names assigned outside loops/comprehensions (loop counters are fine)."""
    skip = _loop_names(fn) | {"_"}
    stores = (n for n in ast.walk(fn) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store))
    return sorted({(n.lineno, n.id) for n in stores if len(n.id) == 1 and n.id not in skip})


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

TOKEN_RX = re.compile(r"\{|\}|\b(if|for|while|switch|catch|match|loop|else)\b|&&|\|\||\?")
BRANCH_WORDS = ("if", "for", "while", "switch", "catch", "match", "loop")


class _TokenWalk:
    """Brace-language metrics from a cleaned body: nesting depth, cyclomatic and cognitive complexity."""
    def __init__(self, start_line: int):
        self.start_line, self.depth, self.cur = start_line, 0, 0
        self.cog, self.cyc, self.items, self.deepest_line = 0, 1, [], start_line

    def feed(self, tok: str, line: int):
        if tok == "{":
            self.cur += 1
            if self.cur > self.depth:
                self.depth, self.deepest_line = self.cur, line
        elif tok == "}":
            self.cur -= 1
        elif tok in BRANCH_WORDS:
            inc = 1 + max(self.cur - 1, 0)
            self.cyc += 1; self.cog += inc
            self.items.append((line, inc, f"{tok} (+1, nesting +{max(self.cur - 1, 0)})" if self.cur > 1 else f"{tok} (+1)"))
        else:
            self.cyc += tok != "else"; self.cog += 1
            self.items.append((line, 1, {"else": "else (+1)", "?": "ternary (+1)"}.get(tok, "boolean operator (+1)")))


def _params_of(head: str) -> int:
    m = re.search(r"\(([^)]*)\)", head)
    return len([p for p in (m.group(1).split(",") if m else []) if p.strip() and p.strip() not in ("self", "&self", "&mut self", "this")])


def _advice_tokens(cleaned: str, start_line: int):
    """(magic numbers, single-letter names) with their lines."""
    magic = sorted({(start_line + cleaned.count("\n", 0, m.start()), float(m.group(0))) for m in re.finditer(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", cleaned)
                    if float(m.group(0)) not in PLAIN_NUMBERS})
    short = sorted({(start_line + cleaned.count("\n", 0, m.start()), m.group(1)) for m in re.finditer(r"\b(?:let|const|var|mut)\s+([a-zA-Z])\b", cleaned) if m.group(1) not in LOOP_VARS})
    return magic, short


def analyse_tokens(file: Path, name: str, header_end: int, text: str, lang: str):
    start_line = text.count("\n", 0, header_end) + 1
    body = brace_block(text, header_end)
    head = text[text.rfind("\n", 0, header_end) + 1:header_end]
    cleaned = re.sub(r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", " ", body, flags=re.S)
    walk = _TokenWalk(start_line)
    for m in TOKEN_RX.finditer(cleaned):
        walk.feed(m.group(0), start_line + cleaned.count("\n", 0, m.start()))
    before = text[max(0, text.rfind("\n", 0, text.rfind("\n", 0, header_end))):header_end]
    magic, short = _advice_tokens(cleaned, start_line)
    return dict(name=name, file=rel(file), line=start_line, lang=lang, lines=body.count("\n") + 1, params=_params_of(head), cyclomatic=walk.cyc,
                cognitive=walk.cog, cognitive_items=walk.items, nesting=max(walk.depth - 1, 0), deepest=(walk.deepest_line, walk.deepest_line),
                docstring=any(x in before for x in ("///", "/**", "*/", "//")), public=not name.startswith("_"), short_names=short, magic=magic, fname=name, src=body,
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


def _func_target(spec: str, sep: str):
    if sep not in spec:
        return None
    path, name = spec.rsplit(sep, 1)
    f = resolve_file(path)
    return ("func", f, name) if f and name else None


def parse_target(spec: str):
    """-> ('dir', Path) | ('file', Path) | ('func', Path, name) | None. Accepts path:func, path::Class.m, path/func."""
    for sep in ("::", ":"):  # explicit function separators first: "a.py::m" must not be read as a file
        t = _func_target(spec, sep)
        if t:
            return t
    p = ROOT / spec if not Path(spec).is_absolute() else Path(spec)
    if p.is_dir():
        return ("dir", p)
    f = resolve_file(spec)
    if f:
        return ("file", f)
    return _func_target(spec, "/")


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
