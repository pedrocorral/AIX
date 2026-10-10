"""Leaf: the contract of a file, the public names other code may call, each with its signature, and the rule that
says whether a change to them breaks a caller. What an isolation exposes is its contract (`aix code isolations`
records it with --accept and fails on a breaking change).

  Python      `__all__` when defined, else public functions (parameters, `=` for a default), classes and their
              public methods, UPPER_CASE constants
  JS/TS       exported functions (parameters, `?` for optional), classes, consts, types, `export {..}` names
  Java        public types and public methods and constructors (parameter types: overloads are separate names);
              an interface's methods are public
  Rust        `pub fn` (parameters), `pub struct|enum|trait|type|const|static|mod`
  ABAP        the PUBLIC SECTION methods of a class or interface (IMPORTING parameters)

Breaking: a name removed, or a signature changed. Python and JS/TS allow a new parameter at the end that has a
default or is optional; every other change of a signature breaks. Types inside signatures are not compared, except
Java's (they name the overload)."""
import ast, re
from pathlib import Path

from bracecomments import strip_strings
from codefiles import EXT


def surface(f: Path) -> dict:
    """name -> signature of the public names of one file ({} for a file that does not parse)."""
    lang = EXT.get(f.suffix)
    text = f.read_text(encoding="utf-8", errors="replace")
    return {"python": _python, "js": _js, "java": _java, "rust": _rust, "abap": _abap}.get(lang, lambda _t: {})(text)


# ---- Python ---------------------------------------------------------------------------------------------------------

def _positional(args) -> list:
    pos = args.posonlyargs + args.args
    defaults = [False] * (len(pos) - len(args.defaults)) + [True] * len(args.defaults)
    return [p.arg + ("=" if has else "") for p, has in zip(pos, defaults)]


def _keyword_part(args) -> list:
    star = ["*" + args.vararg.arg] if args.vararg else (["*"] if args.kwonlyargs else [])
    keywords = [k.arg + ("=" if default is not None else "") for k, default in zip(args.kwonlyargs, args.kw_defaults)]
    return star + keywords + (["**" + args.kwarg.arg] if args.kwarg else [])


def _py_params(fn, skip_self: bool = False) -> str:
    """`(a, b=, *, c, **kw)`: the names in order, `=` where a default makes the parameter optional."""
    pos = _positional(fn.args)
    pos = pos[1:] if skip_self and pos and pos[0].rstrip("=") in ("self", "cls") else pos
    return "(" + ", ".join(pos + _keyword_part(fn.args)) + ")"


def _is_all(node) -> bool:
    return isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets)


def _py_all(tree) -> list | None:
    """The names of `__all__` when the module defines it as a literal list or tuple, else None."""
    node = next((n for n in tree.body if _is_all(n)), None)
    if node is None or not isinstance(node.value, (ast.List, ast.Tuple)):
        return None
    return [e.value for e in node.value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]


def _py_class(node) -> dict:
    out = {node.name: "class"}
    for sub in node.body:
        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and (not sub.name.startswith("_") or sub.name == "__init__"):
            out[f"{node.name}.{sub.name}"] = _py_params(sub, skip_self=True)
    return out


def _py_node(node) -> dict:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return {node.name: _py_params(node)}
    if isinstance(node, ast.ClassDef):
        return _py_class(node)
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        return {t.id: "const" for t in targets if isinstance(t, ast.Name) and t.id.isupper()}
    return {}


def _python(text: str) -> dict:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    names = _py_all(tree)
    out = {}
    for node in tree.body:
        for name, sig in _py_node(node).items():
            if (names is None and not name.split(".")[0].startswith("_")) or (names is not None and name.split(".")[0] in names):
                out[name] = sig
    for name in names or []:
        out.setdefault(name, "name")   # re-exported through __all__: the name is the contract
    return out


# ---- JS / TS --------------------------------------------------------------------------------------------------------

JS_FUNCTION = re.compile(r"\bexport\s+(?:default\s+)?(?:async\s+)?function\s*\*?\s*(\w+)\s*(?:<[^>(]*>)?\s*\(")
JS_DECL = re.compile(r"\bexport\s+(?:default\s+)?(?:declare\s+)?(?:abstract\s+)?(class|const|let|var|interface|type|enum)\s+(\w+)")
JS_ARROW = re.compile(r"\bexport\s+const\s+(\w+)\s*(?::[^=]+)?=\s*(?:async\s+)?\(")
ARROW_TAIL = re.compile(r"\s*(?::[^=;{]+)?=>")
JAVA_TAIL = re.compile(r"\s*(?:throws\s+[\w.,\s]+)?[{;]")
JS_LIST = re.compile(r"\bexport\s+(?:type\s+)?\{([^}]*)\}")


def balanced(code: str, open_at: int) -> tuple:
    """(the text inside the bracket opened at open_at, the index after its closing one): `(cb: () => void)` whole."""
    depth = 0
    for i in range(open_at, len(code)):
        depth += {"(": 1, ")": -1}.get(code[i], 0)
        if depth == 0:
            return code[open_at + 1:i], i + 1
    return code[open_at + 1:], len(code)


def heads(pattern, code: str, tail=None) -> list:
    """(match, parameters) for every head the pattern finds up to its `(`, the parameters read to the balanced `)`;
    with `tail`, only the heads whose closing `)` the tail follows (`=>` of an arrow, `{` or `;` of a method)."""
    out = []
    for m in pattern.finditer(code):
        params, after = balanced(code, m.end() - 1)
        if tail is None or tail.match(code, after):
            out.append((m, params))
    return out


def split_top(s: str) -> list:
    """Top-level comma-separated parts, brackets of any kind respected; an arrow (`=>`, `->`) is no bracket and no
    default value."""
    s = s.replace("=>", "\u2192").replace("->", "\u2192")
    parts, depth, cur = [], 0, ""
    for ch in s:
        depth += {"(": 1, "[": 1, "{": 1, "<": 1, ")": -1, "]": -1, "}": -1, ">": -1}.get(ch, 0)
        if ch == "," and depth == 0:
            parts.append(cur.strip()); cur = ""
            continue
        cur += ch
    return [p for p in parts + [cur.strip()] if p]


def _js_params(raw: str) -> str:
    out = []
    for p in split_top(raw):
        name = re.match(r"(\.\.\.)?\s*([\w$]+|\{[^}]*\}|\[[^\]]*\])\s*(\?)?", p)
        if name:
            optional = bool(name.group(3)) or "=" in p.split(":")[0] or "=" in p
            out.append((name.group(1) or "") + ("{..}" if name.group(2).startswith("{") else name.group(2)) + ("?" if optional else ""))
    return "(" + ", ".join(out) + ")"


def _js(text: str) -> dict:
    code = strip_strings(text, "js")
    out = {m.group(2): m.group(1) for m in JS_DECL.finditer(code)}
    out.update({m.group(1): _js_params(params) for m, params in heads(JS_ARROW, code, ARROW_TAIL)})
    out.update({m.group(1): _js_params(params) for m, params in heads(JS_FUNCTION, code)})
    for m in JS_LIST.finditer(code):
        for part in split_top(m.group(1)):
            out.setdefault(re.split(r"\s+as\s+", part.replace("type ", "").strip())[-1], "name")
    if re.search(r"\bexport\s+default\b", code):
        out.setdefault("default", "default")
    return out


# ---- Java -----------------------------------------------------------------------------------------------------------

JAVA_TYPE = re.compile(r"\bpublic\s+(?:(?:abstract|final|static|sealed|non-sealed|strictfp)\s+)*(class|interface|enum|record|@interface)\s+(\w+)")
JAVA_METHOD = re.compile(r"\bpublic\s+(?:(?:static|final|abstract|synchronized|default|native|strictfp)\s+)*(?:<[^>]*>\s*)?(?:[\w.$\[\]<>?,\s]+?\s+)?(\w+)\s*\(")
JAVA_ABSTRACT = re.compile(r"^\s*(?:(?:static|default)\s+)?(?:<[^>]*>\s*)?[\w.$\[\]<>?,]+(?:\s*<[^;(]*>)?\s+(\w+)\s*\(", re.M)   # an interface's methods, default ones included


def _java_types(raw: str) -> str:
    """`(Map<String, Integer> m, int... n)` -> `(Map<String,Integer>, int...)`: the types name the overload."""
    types = []
    for p in split_top(raw):
        p = re.sub(r"@\w+(?:\([^)]*\))?\s*|\bfinal\s+", "", p).strip()
        types.append(re.sub(r"\s+", "", p.rsplit(None, 1)[0]) if " " in p else p)
    return "(" + ", ".join(types) + ")"


def _java(text: str) -> dict:
    code = strip_strings(text, "java")
    out = {m.group(2): m.group(1) for m in JAVA_TYPE.finditer(code)}
    out.update({f"{m.group(1)}{_java_types(params)}": "method" for m, params in heads(JAVA_METHOD, code, JAVA_TAIL)})
    if re.search(r"\binterface\s+\w+", code):
        keywords = {"return", "new", "throw", "if", "while", "for", "switch"}
        out.update({f"{m.group(1)}{_java_types(params)}": "method" for m, params in heads(JAVA_ABSTRACT, code, JAVA_TAIL) if m.group(1) not in keywords})
    return out


# ---- Rust -----------------------------------------------------------------------------------------------------------

RUST_FN = re.compile(r"\bpub(?:\([^)]*\))?\s+(?:const\s+)?(?:async\s+)?(?:unsafe\s+)?(?:extern\s+\"[^\"]*\"\s+)?fn\s+(\w+)\s*(?:<[^>(]*>)?\s*\(")
RUST_ITEM = re.compile(r"\bpub(?:\([^)]*\))?\s+(struct|enum|trait|type|const|static|mod|union)\s+(\w+)")


def _rust_params(raw: str) -> str:
    names = [re.split(r"\s*:", p, maxsplit=1)[0].strip() for p in split_top(raw)]
    return "(" + ", ".join(n for n in names if n) + ")"


def _rust(text: str) -> dict:
    code = strip_strings(text, "rust")
    out = {m.group(2): m.group(1) for m in RUST_ITEM.finditer(code)}
    for m, params in heads(RUST_FN, code):
        sig = _rust_params(params)
        out[m.group(1)] = sig if m.group(1) not in out or out[m.group(1)] == sig else " | ".join(sorted({out[m.group(1)], sig}))
    return out


# ---- ABAP -----------------------------------------------------------------------------------------------------------

def _abap(text: str) -> dict:
    import abapdefs, abapstyle
    out = {}
    for name, cls in abapdefs.definitions(abapstyle.statements(text.splitlines())).items():
        out[name] = "interface" if cls.interface else "class"
        for m, info in cls.methods.items():
            if info["section"] == "PUBLIC" or cls.interface:
                out[f"{name}=>{m}"] = "(" + ", ".join(info["importing"]) + ")"
    return out


# ---- what breaks a caller -------------------------------------------------------------------------------------------

def _params(sig: str):
    return [p.strip() for p in split_top(sig[1:-1])] if sig.startswith("(") and sig.endswith(")") else None


def compatible(old: str, new: str, lang: str) -> bool:
    """True when every caller of `old` still works with `new`: the same signature, or (Python, JS/TS) the same
    parameters followed by new ones that have a default or are optional."""
    if old == new:
        return True
    po, pn = _params(old), _params(new)
    if lang not in ("python", "js") or po is None or pn is None or pn[:len(po)] != po:
        return False
    return all(p.endswith(("=", "?")) or p.startswith("*") for p in pn[len(po):])


def breaking(recorded: dict, current: dict, lang: str) -> list:
    """(name, what happened) for every recorded name a caller can no longer use as it did."""
    out = []
    for name, sig in sorted(recorded.items()):
        if name not in current:
            out.append((name, "removed"))
        elif not compatible(sig, current[name], lang):
            out.append((name, f"changed {sig} -> {current[name]}"))
    return out
