"""Leaf: the pass-through wrapper rule of `aix code style`. A function whose only statement forwards its own
parameters, unchanged and in order, to one call: Python by AST, the other languages by the body text. Not a wrapper:
a decorated function, a factory naming a constructor, a trait or interface method, an adapter that adds, drops,
reorders or transforms an argument."""
import ast, re


def _forwarded_names(call) -> list:
    """The argument names of a call when every argument is a bare name (or a starred bare name); else None."""
    names = []
    for a in call.args:
        inner = a.value if isinstance(a, ast.Starred) else a
        if not isinstance(inner, ast.Name):
            return None
        names.append(inner.id)
    for k in call.keywords:
        if not isinstance(k.value, ast.Name):
            return None
        names.append(k.value.id)
    return names


def _callee_name(func) -> str:
    """`target`, `mod.target`, `self.other`: a function or method named directly; None for a computed expression."""
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        return f"{func.value.id}.{func.attr}"
    return None


def _single_call(fn):
    """The one call a function's body consists of (docstring aside), else None."""
    body = [s for s in fn.body if not (isinstance(s, ast.Expr) and isinstance(getattr(s, "value", None), ast.Constant))]
    if len(body) != 1 or not isinstance(body[0], (ast.Return, ast.Expr)):
        return None
    return body[0].value if isinstance(body[0].value, ast.Call) else None


def _own_params(fn) -> list:
    params = [a.arg for a in fn.args.args + fn.args.kwonlyargs if a.arg not in ("self", "cls")]
    return params + [a.arg for a in (fn.args.vararg, fn.args.kwarg) if a]


def _forwards_exactly(call, params: list) -> bool:
    """Positional arguments are the parameters in order; keyword arguments are the remaining ones in any order."""
    names = _forwarded_names(call)
    if names is None:
        return False
    positional, keywords = names[:len(call.args)], sorted(names[len(call.args):])
    return positional == params[:len(positional)] and keywords == sorted(params[len(positional):])


def passthrough_py(fn):
    """The callee when the function only forwards its own parameters to one call (a pass-through wrapper), else None.
    Not a wrapper: a decorated function (the framework calls it), a factory naming a constructor (`Thing(x)`), `super()`."""
    call = None if fn.decorator_list else _single_call(fn)
    callee = _callee_name(call.func) if call else None
    if not callee or callee.split(".")[-1][:1].isupper():
        return None
    return callee if _forwards_exactly(call, _own_params(fn)) else None


def _param_names(head: str, name: str, lang: str) -> list:
    """Parameter names in order: `x: T` (TS, Rust), `T x` (Java), `x` (JS); receivers (`self`, `this`) left out.
    The parameters are the parentheses after the function's name (`pub(crate) fn f(` has other parentheses first)."""
    m = re.search(rf"\b{re.escape(name)}\b[^(]*\(((?:[^()]|\([^()]*\))*)\)", head)
    names = []
    for p in (_split_top(m.group(1)) if m else []):
        p = re.sub(r"=.*$", "", p.strip())
        if not p or p in ("self", "&self", "&mut self", "mut self", "this"):
            continue
        names.append(p.split(" ")[-1] if lang == "java" else p.split(":")[0].strip().lstrip("&").replace("mut ", "").strip(".").rstrip("?"))
    return names


def _split_top(params: str) -> list:
    """Split on the commas outside every `<>`, `()` and `[]`: `Vec<(&str, T<'a>)>, x: u8` is two parameters."""
    out, depth, cur = [], 0, ""
    for ch in params:
        depth += ch in "<([" 
        depth -= ch in ">)]"
        if ch == "," and depth == 0:
            out.append(cur); cur = ""
        else:
            cur += ch
    return out + [cur]


PASS_RX = re.compile(r"^\s*(?:return\s+)?(?:await\s+)?([A-Za-z_][\w.:]*)\s*\((.*)\)\s*;?\s*$", re.S)


KEEP_CALLEES = ("super", "this", "new")


def _trait_impl(text: str, header_end: int) -> bool:
    """Rust: the nearest `impl` line above is `impl Trait for Type`, whose methods the trait dictates."""
    heads = re.findall(r"^\s*impl\b[^{\n]*", text[:header_end], re.M)
    return bool(heads) and " for " in heads[-1]


def passthrough_tokens(cleaned: str, head: str, name: str, lang: str, exempt: bool):
    """The callee when the body is one `[return] callee(params)` forwarding the parameters unchanged; see passthrough_py."""
    inner = cleaned.strip()[1:-1] if cleaned.strip().startswith("{") else cleaned
    m = PASS_RX.match(inner.strip())
    last = m.group(1).split(".")[-1].split("::")[-1] if m else ""
    if exempt or not m or last in KEEP_CALLEES or last[:1].isupper():
        return None
    args = [a.strip() for a in re.split(r",(?![^<(\[]*[>)\]])", m.group(2)) if a.strip()]
    return m.group(1) if args == _param_names(head, name, lang) else None
