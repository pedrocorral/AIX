"""Leaf: function-level call graphs for JavaScript/TypeScript, Rust and Java, by tokens, the same approximation
Python gets by AST. Nodes are the functions the style tool finds (`file:f`, `file:Class.method`); an arc is a call
resolved by name: a function of the same file, a name imported by name, `this.m()` / `self.m()` inside a class or
impl, `Class.m()` / `Type::m()` on a class defined or imported in the file. A method on a value whose class the
tool does not know is not an arc and not counted: the report says how many calls could be resolved."""
import re
from pathlib import Path

from clones import FUNC_HEAD, KEYWORDS, brace_block
from codefiles import EXT, rel
from pyfuncgraph import RESOLUTION
from depedges import RS_USE, _alias_bases, _java_imports, _java_index, _java_visible, _resolve_js, _rust_base, _rust_resolve
from hygiene import DECLARE, STRINGS_COMMENTS, STRINGS_COMMENTS_JS
from passthrough import _param_names

BARE_CALL = re.compile(r"(?<![\w$.:])([A-Za-z_$][\w$]*)\s*\(")
RECEIVER_CALL = re.compile(r"(?<![\w$])([A-Za-z_$][\w$]*)(?:\.|::)([A-Za-z_$][\w$]*)\s*\(")
CONSTRUCTED_CALL = re.compile(r"\bnew\s+([A-Z]\w*)\s*\([^()]*\)\s*\.(\w+)\s*\(")   # `new Main().run()`: a call on a fresh instance of a known class
NOT_CALLS = set(KEYWORDS) | {"if", "for", "while", "switch", "catch", "return", "new", "function", "typeof", "await", "super", "constructor", "match",
                             "loop", "unsafe", "fn", "impl", "let", "else", "in", "instanceof", "yield", "delete", "void", "throw", "async", "struct",
                             "enum", "try", "assert", "require", "import", "Some", "Ok", "Err", "Box", "Vec", "String", "println", "format", "vec", "panic",
                             "parseInt", "parseFloat", "isNaN", "isFinite", "setTimeout", "setInterval", "clearTimeout", "clearInterval", "setImmediate", "queueMicrotask",
                             "encodeURIComponent", "decodeURIComponent", "encodeURI", "decodeURI", "fetch", "alert", "structuredClone", "requestAnimationFrame",
                             "Number", "Boolean", "Array", "Object", "Error", "TypeError", "RangeError", "RegExp", "Date", "Promise", "Symbol", "Map", "Set", "WeakMap", "Buffer", "BigInt",
                             "expect", "describe", "it", "test", "beforeEach", "afterEach", "beforeAll", "afterAll", "jest", "vi", "assert_eq", "assert_ne", "assert", "debug_assert"}
IDENT = re.compile(r"[A-Za-z_$][\w$]*")
DESTRUCTURED = re.compile(r"\b(?:const|let|var)\s*[\[{]([^}\]]*)[}\]]\s*=")   # `const { t } = useI18n()`: t holds a value
SELF = {"this", "self", "Self"}
CLASS_HEAD = {"js": re.compile(r"\bclass\s+(\w+)"), "java": re.compile(r"\b(?:class|interface|enum|record)\s+(\w+)"),
              "rust": re.compile(r"\bimpl(?:<[^>]*>)?\s+(?:[\w:<>]+\s+for\s+)?(\w+)")}
ANON_PARAMS = re.compile(r"\bfunction\s*\*?\s*\(([^()]*)\)|\(([^()]*)\)\s*(?::[^=]*)?=>|\|([^|]*)\|")   # callbacks and closures: their parameters are values
DEFAULT_EXPORT = re.compile(r"module\.exports\s*=\s*require\(\s*['\"]([^'\"]+)['\"]\s*\)|module\.exports\s*=\s*(?:exports\s*=\s*)?(\w+)|export\s+default\s+(?:function\s+)?(\w+)")   # the re-export form first
JS_IMPORT_NAMES = re.compile(r"^[ \t]*import\s+(?:type\s+)?(?:(\w+)\s*,?\s*)?(?:\{([^}]*)\}|\*\s+as\s+(\w+))?\s*from\s*['\"]([^'\"]+)['\"]"
                             r"|^[ \t]*(?:const|let|var)\s+(?:(\w+)|\{([^}]*)\})\s*=\s*require\(\s*['\"]([^'\"]+)['\"]\s*\)", re.M)
RS_USE_NAMES = re.compile(r"^\s*(?:pub\s+)?use\s+([\w:]+?)(?:::\{([^}]*)\})?\s*;", re.M)


def _strip(text: str, lang: str) -> str:
    """Comments and strings gone, newlines kept, so positions and line numbers still mean something."""
    rx = STRINGS_COMMENTS_JS if lang == "js" else STRINGS_COMMENTS
    return rx.sub(lambda m: "\n" * m.group(0).count("\n"), text)


def _class_ranges(clean: str, lang: str) -> list:
    """(class name, body start, body end) for every class / impl / interface in the file."""
    out = []
    for m in CLASS_HEAD[lang].finditer(clean):
        body = brace_block(clean, m.end())
        start = clean.find("{", m.end())
        if body and start >= 0:
            out.append((m.group(1), start, start + len(body)))
    return out


def _callback_params(body: str) -> set:
    """Every identifier in the parameter lists of the callbacks and closures inside a body (`function (req, res,
    next)`, `({ onChange }: Props) =>`, `|acc, x|`): values, whatever their types are called."""
    out = set()
    for m in ANON_PARAMS.finditer(body):
        out |= set(IDENT.findall(next(g for g in m.groups() if g is not None)))
    return out


def _values(head: str, name: str, body: str, lang: str) -> set:
    """Names that hold values inside a function: its parameters, its locals (destructured ones too), the parameters
    of the callbacks inside it; not the nested functions, which are nodes."""
    values = set(_param_names(head, name, lang)) | {d.group(1) for d in DECLARE[lang].finditer(body)} | _callback_params(body)
    values |= {n for d in DESTRUCTURED.finditer(body) for n in IDENT.findall(d.group(1))}
    functions = {next(g for g in m.groups() if g) for m in FUNC_HEAD[lang].finditer(body)}
    return {v for v in values if v} - functions


def _enclosing_class(pos: int, classes: list):
    inner = [c for c in classes if c[1] <= pos < c[2]]
    return min(inner, key=lambda c: c[2] - c[1])[0] if inner else None


class _File:
    """One source file: its functions with their class and body, its classes, and what its imports bind."""
    def __init__(self, f: Path, lang: str):
        self.f, self.lang, self.rel = f, lang, rel(f)
        self.text = f.read_text(encoding="utf-8", errors="replace")
        self.clean = _strip(self.text, lang)
        self.classes = _class_ranges(self.clean, lang)
        self.functions = self._functions()
        declared = {d.group(1) for d in DECLARE[lang].finditer(self.clean) if not self.owner(d.start())}
        declared |= {n for d in DESTRUCTURED.finditer(self.clean) if not self.owner(d.start()) for n in IDENT.findall(d.group(1))}
        self.values = declared - {fx[1] for fx in self.functions}   # module-level variables; `const f = () => {}` is a function, not a value
        self.imports = {}   # local name -> (file, name or None): None means the module or class itself
        self.externals = set()   # names bound by imports of packages: their calls are outside A, not misses

    def _functions(self) -> list:
        """(node, simple name, class, body start, body end), innermost function owning a position wins."""
        out = []
        for m in FUNC_HEAD[self.lang].finditer(self.clean):
            name = next((g for g in m.groups() if g), None)
            brace = self.clean.find("{", m.end() - 1)
            if not name or (self.lang != "rust" and name in KEYWORDS) or brace < 0 or ";" in self.clean[m.end() - 1:brace]:
                continue   # `else if (` looks like a function head in JS and Java; Rust's `fn new` is a function
            body = brace_block(self.clean, m.end() - 1)
            cls = _enclosing_class(brace, self.classes)
            head = self.clean[self.clean.rfind("\n", 0, m.end() - 1) + 1:brace]
            out.append((f"{self.rel}:{cls + '.' if cls else ''}{name}", name, cls, brace, brace + len(body), _values(head, name, body, self.lang)))
        return out

    def owner(self, pos: int):
        """The innermost function whose body holds a position."""
        inside = [fx for fx in self.functions if fx[3] <= pos < fx[4]]
        return min(inside, key=lambda fx: fx[4] - fx[3]) if inside else None


# ---- what the imports bind ------------------------------------------------------------------------------------------

def _js_target(spec: str, file: _File, files: dict):
    """The project file an import specifier names, relative or through tsconfig aliases; None when it is a package."""
    bases = [file.f.parent / spec] if spec.startswith(".") else _alias_bases(spec, file.f)
    target = next((h for h in map(_resolve_js, bases) if h), None)
    return rel(target) if target is not None and rel(target) in files else None


def _bind_named(file: _File, target: str, named: str):
    """`{ a, b as c, type T }` binds a -> a, c -> b, T -> T of the target file."""
    for part in named.split(","):
        original, _, local = part.strip().removeprefix("type ").partition(" as ")
        if original.strip():
            file.imports[(local or original).strip()] = (target, original.strip())


def _bound_by(m) -> tuple:
    """(names bound to the whole module, the `{...}` clause, the specifier) of one import or require line."""
    default, named, star, spec, req_name, req_named, req_spec = m.groups()
    return [n for n in (default, star, req_name) if n], named or req_named or "", spec or req_spec


def _js_imports(file: _File, files: dict):
    for m in JS_IMPORT_NAMES.finditer(file.text):
        wholes, named, spec = _bound_by(m)
        target = _js_target(spec, file, files)
        if target is None:
            file.externals |= set(wholes) | {p.strip().split(" as ")[-1].strip() for p in named.split(",") if p.strip()}
            continue
        for whole in wholes:
            file.imports[whole] = (target, None)   # the module itself: `whole.f()`
        _bind_named(file, target, named)


def _rust_module(path: list, file: _File, crate_root: Path, files: dict):
    """The project file a `crate::` / `super::` / `self::` path names, else None."""
    if not path or path[0] not in ("crate", "super", "self"):
        return None
    base = _rust_base(re.match(r"use\s+(.+)", "use " + "::".join(path)), file.f, crate_root)
    hit = _rust_resolve(*base) if base else None
    return rel(hit) if hit is not None and rel(hit) in files else None


def _rust_modules(file: _File, crate_root: Path, files: dict):
    """`mod x;` and whole-module uses bind the module's name: `x::f()`."""
    for m in RS_USE.finditer(file.text):
        where = _rust_base(m, file.f, crate_root)
        hit = _rust_resolve(*where) if where else None
        if hit and rel(hit) in files:
            file.imports[m.group(1).split("::")[-1]] = (rel(hit), None)


def _rust_imports(file: _File, files: dict):
    crate_root = next((p for p in file.f.parents if (p / "Cargo.toml").exists()), file.f.parent) / "src"
    _rust_modules(file, crate_root, files)
    for m in RS_USE_NAMES.finditer(file.text):   # `use crate::a::b::helper;` and `use crate::a::b::{c, d as e};`
        path, braces = m.group(1).split("::"), m.group(2)
        target = _rust_module(path[:-1] if braces is None else path, file, crate_root, files)
        if target:
            _bind_named(file, target, path[-1] if braces is None else braces)
        elif path[0] not in ("crate", "super", "self"):
            file.externals |= {n.strip().split(" as ")[-1].strip() for n in ([path[-1]] if braces is None else braces.split(","))}


def _java_visible_classes(file: _File, files: dict, java_idx: dict):
    for hit in _java_imports(file.text, java_idx["paths"]):
        if rel(hit) in files:
            file.imports[hit.stem] = (rel(hit), None)
    for cls, hit in _java_visible(file.text, java_idx).items():
        if rel(hit) in files:
            file.imports[cls] = (rel(hit), None)


# ---- resolution -------------------------------------------------------------------------------------------------------

def _resolve_bare(name: str, file: _File, cls, defs: dict):
    """`helper()`: a function of this file (a method of the same class first, for Java), then an imported name."""
    if cls and (file.rel, f"{cls}.{name}") in defs:
        return defs[(file.rel, f"{cls}.{name}")]
    if (file.rel, name) in defs:
        return defs[(file.rel, name)]
    target = file.imports.get(name)
    if not target:
        return None
    return defs.get((target[0], target[1])) if target[1] else _default_export(target[0], defs)


def _default_export(file_rel: str, defs: dict, depth: int = 3):
    """What `require('./x')()` calls: the function `module.exports` / `export default` names, followed through a
    facade that re-exports another file, a few levels at most."""
    from codefiles import ROOT
    text = (ROOT / file_rel).read_text(encoding="utf-8", errors="replace") if depth else ""
    m = DEFAULT_EXPORT.search(text)
    if not m:
        return None
    if m.group(1):
        target = _resolve_js((ROOT / file_rel).parent / m.group(1))
        return _default_export(rel(target), defs, depth - 1) if target else None
    return defs.get((file_rel, m.group(2) or m.group(3)))


def _resolve_receiver(receiver: str, method: str, file: _File, cls, defs: dict):
    """`this.m()` / `self.m()` / `Type::m()` / `Class.m()` / `module.f()`."""
    if receiver in SELF:
        return defs.get((file.rel, f"{cls}.{method}")) if cls else None
    if any(c[0] == receiver for c in file.classes):
        return defs.get((file.rel, f"{receiver}.{method}"))
    target = file.imports.get(receiver)
    if target is None:
        return None
    return defs.get((target[0], f"{receiver}.{method}")) or defs.get((target[0], method))


def _is_project_call(receiver, method, file: _File, cls) -> bool:
    """`this.m()` counts only when the class defines m (an inherited method is nobody's node here)."""
    if receiver in SELF:
        return bool(cls) and (file.rel, f"{cls}.{method}") in _DEFS
    return any(c[0] == receiver for c in file.classes) or receiver in file.imports


def _record(owner, target, edges: set):
    """Count the call as seen, and as matched when it resolved; an arc unless it is the function calling itself."""
    RESOLUTION["seen"] += 1
    RESOLUTION["matched"] += bool(target)
    if target and target != owner[0]:
        edges.add((owner[0], target))


def _plausible_bare(file: _File, m, owner) -> bool:
    """A bare call name resolution may match: not a keyword, a global, a library import, a constructor, the function
    itself; in Java a bare name is a method of the class or inherited, so only what matches is a project call."""
    name = m.group(1)
    module_value = name in file.values and name not in file.imports   # `const app = require('./x')` binds a module, not a value
    if name in NOT_CALLS or name in file.externals or name == owner[1] or name in owner[5] or module_value or file.clean[max(0, m.start() - 4):m.start()].endswith("new "):
        return False   # owner[5] and file.values: parameters, locals and module variables hold values, not functions
    return file.lang != "java" or bool(owner[2] and (file.rel, f"{owner[2]}.{name}") in _DEFS)


_DEFS = {}


def _bare_edges(file: _File, defs: dict, edges: set):
    for m in BARE_CALL.finditer(file.clean):
        owner = file.owner(m.start())
        if owner and _plausible_bare(file, m, owner):
            _record(owner, _resolve_bare(m.group(1), file, owner[2], defs), edges)


def _receiver_edges(file: _File, defs: dict, edges: set):
    for m in list(RECEIVER_CALL.finditer(file.clean)) + list(CONSTRUCTED_CALL.finditer(file.clean)):
        owner = file.owner(m.start())
        if owner and _is_project_call(m.group(1), m.group(2), file, owner[2]):
            _record(owner, _resolve_receiver(m.group(1), m.group(2), file, owner[2], defs), edges)


def _edges_of(file: _File, defs: dict) -> set:
    edges = set()
    _bare_edges(file, defs, edges)
    _receiver_edges(file, defs, edges)
    return edges


def function_graph_tokens(paths: list) -> tuple:
    """(nodes, edges) for every JS/TS, Rust and Java file under `paths`; RESOLUTION is added to, not reset."""
    from codefiles import source_files
    files = {rel(f): _File(f, EXT[f.suffix]) for f in source_files(paths) if EXT.get(f.suffix) in ("js", "rust", "java")}
    java_idx = _java_index([fx.f for fx in files.values() if fx.lang == "java"])
    defs = {}
    for fx in files.values():
        for node, name, cls, _, _, _ in fx.functions:
            defs[(fx.rel, f"{cls}.{name}" if cls else name)] = node
    for fx in files.values():
        {"js": _js_imports, "rust": _rust_imports, "java": lambda a, b: _java_visible_classes(a, b, java_idx)}[fx.lang](fx, files)
    _DEFS.clear(); _DEFS.update(defs)
    edges = set()
    for fx in files.values():
        edges |= _edges_of(fx, defs)
    return set(defs.values()), edges
