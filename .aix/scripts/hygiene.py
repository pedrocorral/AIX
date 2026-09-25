"""Leaf: the hygiene findings of `aix code style`. Leftovers (an import, a variable or a parameter nothing reads),
swallowed exceptions (a catch that does nothing and says nothing), and the unambiguous bugs (a mutable default in
Python, an assignment inside a condition in JavaScript, `==` on a String in Java). Python by AST; the other
languages by tokens with strings and comments removed first, so a name inside a string never counts as a use."""
import ast, re

ADVICE = {"leftover": "delete it, or use it: a name nothing reads is a lie to the next reader",
          "swallowed": "handle it, log it, re-raise it, or say in a comment why nothing is the right thing to do",
          "bug": "fix it now: this shape is never intended"}
COMMENTS = r"//[^\n]*|/\*.*?\*/"
STRINGS = r"\br#*\"[^\"]*\"#*|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`(?:[^`\\]|\\.)*`"   # Rust raw strings first: a backslash is literal there
STRINGS_COMMENTS = re.compile(COMMENTS + "|" + STRINGS, re.S)
STRINGS_JS = r"\"(?:\\.|[^\"\\\n])*\"|`(?:[^`\\]|\\.)*`"   # no single quotes: an apostrophe in JSX text is not a string start
STRINGS_COMMENTS_JS = re.compile(COMMENTS + "|" + STRINGS_JS, re.S)
INTERPOLATED = re.compile(r"\$\{([^}]*)\}|\{([A-Za-z_]\w*)(?::[^}]*)?\}")   # `${expr}` (JS), `{name}` (Rust format!, Python f-strings)
JSX_TAG = re.compile(r"(?<![\w>])<[a-zA-Z][\w.]*(?:\s[^<>]*)?/?>|</")   # a tag, not a generic (`Array<string>` follows a word)
CALLBACK_PARAMS = {"req", "res", "next", "err", "error", "event", "ctx", "context", "done", "callback", "cb", "reject", "resolve"}
MUTABLE_CALLS = {"list", "dict", "set", "bytearray", "defaultdict", "OrderedDict", "deque"}
RE_EXPORT_FILES = ("__init__.py", "index.ts", "index.tsx", "index.js", "mod.rs", "lib.rs", "compat.py", "_compat.py", "compat.ts", "compat.js")
NOT_IMPLEMENTED = re.compile(r"raise NotImplementedError|throw new UnsupportedOperationException|todo!\(|unimplemented!\(|^\s*(?:pass|\.\.\.)\s*$")


# ---- Python ------------------------------------------------------------------------------------------------------

def _read_names(fn) -> set:
    """Every name loaded anywhere inside the function, nested scopes included; `global`/`nonlocal` count as reads."""
    names = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Load, ast.Del)):
            names.add(n.id)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            names |= set(n.names)
        elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name):
            names.add(n.target.id)   # `x += ...` reads x (and mutates a list the caller passed)
    return names


def _stub_body(fn) -> bool:
    """`pass`, `...`, a docstring, or `raise NotImplementedError`: a hook or an abstract method, its parameters are the contract."""
    body = [s for s in fn.body if not (isinstance(s, ast.Expr) and isinstance(getattr(s, "value", None), ast.Constant))]
    if not body:
        return True
    return len(body) == 1 and (isinstance(body[0], ast.Pass) or (isinstance(body[0], ast.Raise) and "NotImplementedError" in ast.unparse(body[0])))


def _calls_super(fn) -> bool:
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Call)
               and getattr(n.func.value.func, "id", "") == "super" for n in ast.walk(fn))


def _keeps_its_parameters_py(fn, cls) -> bool:
    """Decorated functions, stubs, overrides that call super, public and dunder methods, and tests (pytest injects
    fixtures by parameter name): their parameters are a contract."""
    public = not fn.name.startswith("_") or fn.name.startswith("__")
    return bool(fn.decorator_list) or _stub_body(fn) or _calls_super(fn) or bool(cls and public) or fn.name.startswith("test")


def trailing_unused(params: list, reads: set) -> list:
    """The unused parameters after the last one that is read: an unused parameter before a used one is positional,
    a callback's contract (`def version(ctx, param, value)`); one at the end could simply be dropped."""
    last_read = max((i for i, p in enumerate(params) if p in reads), default=-1)
    return [p for i, p in enumerate(params) if i > last_read and p not in reads and not p.startswith("_")]


def unused_parameters_py(fn, cls=None) -> list:
    """(line, message) for trailing parameters nothing reads."""
    if _keeps_its_parameters_py(fn, cls):
        return []
    reads = _read_names(fn) | {"self", "cls"}
    positional = fn.args.posonlyargs + fn.args.args
    defaulted = {a.arg for a, d in zip(positional[::-1], fn.args.defaults[::-1]) if isinstance(d, ast.Constant) and d.value is None}
    params = [a.arg for a in positional + fn.args.kwonlyargs if a.arg not in defaulted]   # `e=None`: a callback's optional slot
    return [(fn.lineno, f"leftover: parameter `{p}` of `{fn.name}` is never read") for p in trailing_unused(params, reads)]


def _own_scope(fn):
    """The nodes of the function's own body, not those of nested functions and classes (their own scopes)."""
    todo = list(fn.body)
    while todo:
        n = todo.pop()
        yield n
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            todo.extend(ast.iter_child_nodes(n))


def _stores(fn) -> dict:
    """name -> first line assigned, for plain assignments in this function's own scope (not loop targets, not unpacking)."""
    out = {}
    for n in _own_scope(fn):
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            out.setdefault(n.targets[0].id, n.lineno)
        elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value is not None:
            out.setdefault(n.target.id, n.lineno)
    return out


def unused_variables_py(fn) -> list:
    reads = _read_names(fn)
    return [(line, f"leftover: variable `{name}` in `{fn.name}` is assigned and never read") for name, line in _stores(fn).items()
            if name not in reads and not name.startswith("_")]


def _silent_handler(h, lines: list) -> bool:
    """Only `pass` / `...` inside, and no comment on the handler's lines."""
    silent = all(isinstance(s, ast.Pass) or (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)) for s in h.body)
    return silent and not any("#" in lines[i] for i in range(h.lineno, (h.end_lineno or h.lineno)))


def swallowed_py(fn, lines: list) -> list:
    """An except that does nothing (pass, ...) without a comment inside, or a bare `except:` whatever its body."""
    out = []
    for h in (n for n in ast.walk(fn) if isinstance(n, ast.ExceptHandler)):
        if h.type is None and not any(isinstance(s, ast.Raise) for s in h.body):
            out.append((h.lineno, "swallowed: bare `except:` also catches SystemExit and KeyboardInterrupt"))
        elif h.type is not None and "ImportError" not in ast.unparse(h.type) and _silent_handler(h, lines):
            out.append((h.lineno, "swallowed: this except does nothing and says nothing"))   # `except ImportError: pass` is the optional-dependency idiom
    return out


def mutable_defaults_py(fn) -> list:
    out = []
    for a, default in zip(fn.args.args[::-1], fn.args.defaults[::-1]):
        call_of = getattr(getattr(default, "func", None), "id", None)
        if isinstance(default, (ast.List, ast.Dict, ast.Set)) or call_of in MUTABLE_CALLS or (call_of and call_of[:1].isupper() and call_of not in ("None",)):
            out.append((fn.lineno, f"bug: mutable default `{a.arg}={ast.unparse(default)}` is shared between calls"))
    return out


def function_py(fn, lines: list, cls=None, test: bool = False) -> list:
    """Every hygiene finding of one Python function: (line, message). A test may catch to assert nothing more happens."""
    swallowed = [] if test else swallowed_py(fn, lines)
    return sorted(unused_parameters_py(fn, cls) + unused_variables_py(fn) + swallowed + mutable_defaults_py(fn))


def _bound_names(node) -> list:
    """(line, local name) an import statement binds; `from __future__` and `*` bind nothing to check."""
    if isinstance(node, ast.Import):
        return [(node.lineno, (a.asname or a.name).split(".")[0]) for a in node.names]
    if isinstance(node, ast.ImportFrom) and node.module != "__future__":
        return [(node.lineno, a.asname or a.name) for a in node.names if a.name != "*"]
    return []


def _import_names_py(tree) -> list:
    """(line, local name) for every import at module level, `if TYPE_CHECKING:` blocks included."""
    out = []
    for node in tree.body:
        inner = node.body if isinstance(node, ast.If) and "TYPE_CHECKING" in ast.unparse(node.test) else [node]
        for n in inner:
            out += _bound_names(n)
    return out


def _used_names(tree) -> set:
    """Names loaded anywhere, plus every string constant (annotations in quotes, `__all__`), joined for a word search."""
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    used |= {n.value.id for n in ast.walk(tree) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
    strings = " ".join(c.value for c in ast.walk(tree) if isinstance(c, ast.Constant) and isinstance(c.value, str))
    return used | set(re.findall(r"\w+", strings))


def unused_imports_py(tree, text: str, filename: str, reexported: set = frozenset()) -> list:
    """Imports whose name appears nowhere else in the file; re-export files, names other files import from this
    module (`reexported`) and `# noqa` lines are left alone."""
    if filename.endswith(RE_EXPORT_FILES):
        return []
    used, lines = _used_names(tree) | set(reexported), text.splitlines()
    return [(line, f"leftover: unused import `{name}`") for line, name in _import_names_py(tree) if name not in used and "noqa" not in lines[line - 1]]


# ---- JavaScript/TypeScript, Rust, Java by tokens -------------------------------------------------------------------

IMPORTS = {
    "js": re.compile(r"^[ \t]*import\s+(?:type\s+)?(?:(\w+)\s*,?\s*)?(?:\{([^}]*)\}|\*\s+as\s+(\w+))?\s*from\s*['\"][^'\"]+['\"]|^[ \t]*(?:const|let|var)\s+(?:(\w+)|\{([^}]*)\})\s*=\s*require\(", re.M),
    "java": re.compile(r"^[ \t]*import\s+(?:static\s+)?[\w.]*\.(\w+)\s*;", re.M),
}
DECLARE = {"js": re.compile(r"\b(?:const|let|var)\s+(\w+)\s*="), "rust": re.compile(r"(?<!if )(?<!while )\blet\s+(?:mut\s+)?([a-z_]\w*)\s*(?::\s*[^=:][^=]*)?=(?!=)"),   # a binding, not an `if let` pattern
           "java": re.compile(r"(?:^|[;{])\s*(?:final\s+)?(?:[A-Z]\w*(?:<[^>]*>)?|int|long|short|byte|char|boolean|double|float|var)(?:\[\])*\s+(\w+)\s*=(?!=)", re.M)}
SWALLOWED = {"js": re.compile(r"\bcatch\s*(?:\([^)]*\))?\s*\{(\s*)\}|\.catch\(\s*(?:\([^)]*\)|\w+)\s*=>\s*\{(\s*)\}\s*\)"),
             "java": re.compile(r"\bcatch\s*\([^)]*\)\s*\{(\s*)\}"), "rust": re.compile(r"(?!)")}
BUGS = {"js": (re.compile(r"\b(?:if|while)\s*\(((?:[^()]|\([^()]*\))*)\)"), "bug: assignment inside a condition"),
        "java": (re.compile(r"\"\"\s*[!=]=\s*\w|\b\w+\s*[!=]=\s*\"\""), "bug: `==` compares String references, not text: use equals()")}   # strings are `""` by then


def _import_list(m, lang: str) -> list:
    """The local names an import line binds."""
    groups = [g for g in m.groups() if g]
    names = []
    for g in groups:
        for part in g.split(","):
            part = part.strip().split(" as ")[-1].strip()
            if part and part != "self" and not part.startswith("type "):
                names.append(part.split("::")[-1] if lang == "rust" else part)
    return names


def _code_around(text: str, m, lang: str) -> str:
    """The file without the import line and without string text: what a name search may count as a use. Java keeps
    its comments and char literals (`{@link X}` in Javadoc is a use); JS keeps `${x}`, and JSX means React is used."""
    around = text[:m.start()] + text[m.end():]
    if lang == "java":
        return re.sub(r"\"(?:\\.|[^\"\\\n])*\"", " ", around)
    rest = _body_tokens(around, "js")
    return rest + " React" if JSX_TAG.search(rest) else rest


def unused_imports_tokens(text: str, lang: str, filename: str) -> list:
    """JS/TS and Java only: a Rust `use` may bring a trait into scope for its methods, which no name search sees
    (and the compiler already warns)."""
    if lang not in IMPORTS or filename.endswith(RE_EXPORT_FILES):
        return []
    out = []
    for m in IMPORTS[lang].finditer(text):
        rest = _code_around(text, m, lang)
        line = text.count("\n", 0, m.start()) + 1
        out += [(line, f"leftover: unused import `{name}`") for name in _import_list(m, lang) if not re.search(rf"(?<![\w$]){re.escape(name)}(?![\w$])", rest)]
    return out


def _body_tokens(body: str, lang: str = "") -> str:
    """The body without comments and string text; what a string interpolates stays (`${x}`, `{x}`), `...x` reads x."""
    def keep(m):
        text = m.group(0)
        kept = " " if text.startswith(("//", "/*")) else " ".join(g for pair in INTERPOLATED.findall(text) for g in pair if g)
        return kept + "\n" * text.count("\n")   # line numbers of what follows stay right
    return (STRINGS_COMMENTS_JS if lang == "js" else STRINGS_COMMENTS).sub(keep, body).replace("...", " ").replace("..", " ")   # `...x` spreads, `..end` ranges


def _read_in(name: str, text: str) -> bool:
    return bool(re.search(rf"(?<![\w$.]){re.escape(name)}(?![\w$])", text))


def _public_method(fx: dict) -> bool:
    """A method others may override or call by contract: Java non-private, a JS class method, a Rust `pub fn`."""
    head = fx["src_head"]
    if fx["lang"] == "java":
        return "private" not in head
    if fx["lang"] == "rust":
        return head.lstrip().startswith("pub") or "self" in head
    return not re.search(r"\bfunction\b|=>|=", head)   # JS shorthand method inside a class or object


def _keeps_its_parameters(fx: dict, inner: str) -> bool:
    """Hooks, stubs, overrides (decorated), tests, empty bodies and public methods: their parameters are a contract."""
    return fx["decorated"] or fx["test"] or bool(NOT_IMPLEMENTED.search(inner)) or not inner.strip() or _public_method(fx)


def _unused_params_tokens(fx: dict, params: list, inner: str) -> list:
    """JS callback names (req, res, next, err, event, ...) are positional by convention and never reported."""
    if _keeps_its_parameters(fx, inner):
        return []
    skip = {"self", "this"} | (CALLBACK_PARAMS if fx["lang"] == "js" else set())
    plain = [p for p in params if p not in skip and not p.startswith(("{", "["))]   # a destructured parameter is a pattern, not a name
    reads = {p for p in plain if _read_in(p, inner)}
    return [(fx["line"], f"leftover: parameter `{p}` of `{fx['fname']}` is never read") for p in trailing_unused(plain, reads)]


def unused_in_function_tokens(fx: dict, params: list) -> list:
    """Leftover parameters and variables of one token-analysed function."""
    clean = _body_tokens(fx["src"], fx["lang"])
    inner = clean.strip()[1:-1] if clean.strip().startswith("{") else clean
    out = _unused_params_tokens(fx, params, inner)
    for m in DECLARE[fx["lang"]].finditer(inner):
        name = m.group(1)
        if "SuppressWarnings" in inner[max(0, m.start() - 80):m.start()]:
            continue   # `@SuppressWarnings("unused")`: the author said so
        elsewhere = inner[:m.start()] + inner[m.end():]   # a closure above may read a `const` declared below
        if not name.startswith("_") and not _read_in(name, elsewhere):
            out.append((fx["line"] + inner.count("\n", 0, m.start(1)), f"leftover: variable `{name}` in `{fx['fname']}` is assigned and never read"))
    return out


def swallowed_tokens(fx: dict) -> list:
    """A catch with nothing but whitespace inside (a comment inside is intent and survives the raw text check)."""
    raw = fx["src"]
    out = []
    for m in SWALLOWED.get(fx["lang"], SWALLOWED["rust"]).finditer(raw):
        out.append((fx["line"] + raw.count("\n", 0, m.start()), "swallowed: this catch does nothing and says nothing"))
    return out


def _assignment_in_condition(cond: str) -> bool:
    """`=` that is not `==`, `===`, `!=`, `<=`, `>=`, `=>`, and not wrapped in its own parentheses (the on-purpose idiom)."""
    stripped = re.sub(r"\([^()]*\)", "", cond)
    return bool(re.search(r"(?<![=!<>])=(?![=>])", stripped))


def _placeholder(m) -> str:
    """A comment becomes a space, a string `""`, a char literal `''`: the shapes survive, the contents cannot match."""
    text = m.group(0)
    return " " if text[0] == "/" else "''" if text[0] == "'" else '""'


def bugs_tokens(fx: dict) -> list:
    if fx["lang"] not in BUGS:
        return []
    rx, message = BUGS[fx["lang"]]
    clean = _body_tokens(fx["src"], "js") if fx["lang"] == "js" else STRINGS_COMMENTS.sub(_placeholder, fx["src"])
    out = []
    for m in rx.finditer(clean):
        if fx["lang"] == "java" or _assignment_in_condition(m.group(1)):
            out.append((fx["line"] + clean.count("\n", 0, m.start()), message))
    return out


def function_tokens(fx: dict, params: list) -> list:
    """Every hygiene finding of one JS/TS, Rust or Java function: (line, message). A test may catch to assert nothing more happens."""
    return sorted(unused_in_function_tokens(fx, params) + ([] if fx["test"] else swallowed_tokens(fx)) + bugs_tokens(fx))
