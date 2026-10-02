"""Leaf: dead functions and methods in JavaScript/TypeScript, Rust and Java, the Python rule applied by tokens: a
function whose simple name is never referenced anywhere else in the project's files of that language (as a bare
identifier, a member `.name`, a path `::name`) is a candidate, unless something we cannot see calls it: an entry or
test file, an annotation or attribute above it (`@GetMapping`, `#[test]`), a JS export, a Rust trait implementation,
a Java constructor, getter or setter, `main`. Name-based and conservative: a method called through any object of
the same name is live."""
import re
from collections import Counter

from codefiles import EXT, source_files
from funcgraph import IDENT, _File
from graphmetrics import is_test

ANNOTATED = {"java": re.compile(r"^\s*@\w"), "rust": re.compile(r"^\s*#\["), "js": re.compile(r"^\s*@\w")}
JS_EXPORT_LIST = re.compile(r"\bexport\s*\{([^}]*)\}|\bmodule\.exports\s*=\s*\{([^}]*)\}|\bexports\.(\w+)\s*=|\bmodule\.exports\.(\w+)\s*=")
RUST_TRAIT_IMPL = re.compile(r"^[ \t]*impl(?:<[^>]*>)?\s+[\w:<>'&\[\]() ,]+?\s+for\s+\w+", re.M)
JAVA_IMPLICIT = {"main", "readResolve", "writeReplace", "readObject", "writeObject", "readObjectNoData"}   # serialization hooks
JS_IMPLICIT = {"componentDidMount", "componentDidUpdate", "componentWillUnmount", "componentDidCatch", "shouldComponentUpdate",
               "getDerivedStateFromProps", "getSnapshotBeforeUpdate", "render", "constructor", "getDerivedStateFromError"}   # React calls them
PAGE_EXT = (".html", ".htm", ".jinja", ".jinja2", ".j2", ".ejs", ".hbs", ".vue", ".svelte", ".xhtml")   # onclick="doVote()" is a reference


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _head_line(fx: _File, brace: int) -> int:
    """The line the function's head starts on (its name is on it or just above a multi-line signature)."""
    start = fx.clean.rfind("\n", 0, brace)
    return _line_of(fx.clean, start + 1)


def _annotated(fx: _File, brace: int) -> bool:
    """A line starting with an annotation or attribute right above the head (blank lines skipped)."""
    head_start = fx.clean.rfind("\n", 0, brace) + 1
    above = [l for l in fx.clean[:head_start].split("\n") if l.strip()]   # a stripped doc comment leaves a blank line: skipped
    marker = ANNOTATED[fx.lang]
    return bool(above) and (marker.match(above[-1]) is not None or (fx.lang == "java" and above[-1].strip() == ")" and any(marker.match(l) for l in above[-6:])))


STATEMENT_START = re.compile(r"^[ \t]*(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:const|let|var|function|class)\b", re.M)


def _statement(fx: _File, brace: int) -> str:
    """The statement that declares the function: from its `export const` / `function` line to the brace, multi-line heads included."""
    before = fx.clean[:brace]
    starts = [m.start() for m in STATEMENT_START.finditer(before[-1500:])]
    return before[len(before) - 1500 + starts[-1]:] if starts and len(before) >= 1500 else before[starts[-1]:] if starts else before[-200:]


def _exported(fx: _File, name: str, brace: int) -> bool:
    """JS: `export` on the function's own statement (a multi-line head included), or the name in an export list."""
    if fx.lang != "js":
        return False
    if re.search(rf"\bexport\b[^;]*?\b{re.escape(name)}\b", _statement(fx, brace)) or re.search(rf"\bexport\s+default\s+{re.escape(name)}\b", fx.clean):
        return True
    for m in JS_EXPORT_LIST.finditer(fx.clean):
        names = IDENT.findall(m.group(1) or m.group(2) or "") + [m.group(3) or m.group(4) or ""]
        if name in names:
            return True
    return False


def _in_trait_impl(fx: _File, brace: int) -> bool:
    """Rust: the function sits in an `impl Trait for Type` block, the trait calls it."""
    for m in RUST_TRAIT_IMPL.finditer(fx.clean):
        start = fx.clean.find("{", m.end())
        depth, i = 0, start
        while i < len(fx.clean):
            depth += (fx.clean[i] == "{") - (fx.clean[i] == "}")
            if depth == 0:
                break
            i += 1
        if start <= brace < i:
            return True
    return False


def _head(fx: _File, brace: int) -> str:
    return fx.clean[fx.clean.rfind("\n", 0, brace) + 1:brace]


def _object_method(fx: _File, name: str, cls, brace: int) -> bool:
    """JS: a method of an object literal (`beforeSend(event) {` after `{` or `,`, outside any class): the owner of the
    object calls it, a library most often."""
    if fx.lang != "js" or cls:
        return False
    head_start = fx.clean.rfind("\n", 0, brace) + 1
    previous = fx.clean[:head_start].rstrip()
    return previous.endswith(("{", ",")) and re.match(rf"\s*(?:async\s+)?{re.escape(name)}\s*\(", fx.clean[head_start:brace]) is not None


def _hooked(fx: _File, name: str, cls, brace: int) -> bool:
    """Called by the language or a framework rather than by name: a non-private Java method (an override, a bean
    property or a reflective call can reach any of them), a Rust trait impl, a React lifecycle method."""
    if fx.lang == "java":
        return name == cls or name in JAVA_IMPLICIT or not re.search(r"\bprivate\b", _head(fx, brace))
    if fx.lang == "rust":
        return name == "main" or _in_trait_impl(fx, brace)
    return name.startswith("test") or name in JS_IMPLICIT


def _live_by_rule(fx: _File, name: str, cls, brace: int, is_entry) -> bool:
    """Something we cannot see calls it: entry/test file (`is_entry` is deadcode's convention), annotation, export,
    an object-literal method, a hook."""
    return (is_entry(fx.rel) or is_test(fx.rel) or _annotated(fx, brace) or _exported(fx, name, brace)
            or _object_method(fx, name, cls, brace) or _hooked(fx, name, cls, brace))


def _public(fx: _File, name: str, brace: int) -> bool:
    """Reported with the 'public' note: a Rust `pub fn` (the `pub` sits before `fn name`, a multi-line head or not);
    JS and Java candidates are never exported or non-private."""
    if fx.lang != "rust":
        return False
    at = fx.clean.rfind(f"fn {name}", 0, brace)
    return at >= 0 and bool(re.search(r"\bpub\b(?:\([^)]*\))?\s*(?:async\s+|unsafe\s+|const\s+)*$", fx.clean[max(0, at - 40):at]))


def _page_identifiers(roots) -> Counter:
    """Identifiers in templates and pages: `onclick="doVote()"` and `th:onclick` call JS functions by name."""
    from codefiles import ROOT
    out = Counter()
    for root in roots:
        base = ROOT / root
        for f in (base.rglob("*") if base.is_dir() else []):
            if f.suffix in PAGE_EXT and f.is_file():
                out.update(IDENT.findall(f.read_text(encoding="utf-8", errors="replace")))
    return out


def dead_functions(roots, is_entry) -> list:
    """[(file:Class.name, line, public)] for JS/TS, Rust and Java functions never referenced by name outside their
    definition, in the files of their language or, for JS, in the pages that call scripts by name. `is_entry(path)`
    says which files are live by convention (deadcode.is_entry_module)."""
    files = [_File(f, EXT[f.suffix]) for f in source_files(roots) if EXT.get(f.suffix) in ("js", "rust", "java")]
    seen, defined = {"js": _page_identifiers(roots), "rust": Counter(), "java": Counter()}, {"js": Counter(), "rust": Counter(), "java": Counter()}
    for fx in files:
        seen[fx.lang].update(IDENT.findall(fx.clean))
        defined[fx.lang].update(name for _n, name, _c, _b, _e, _v in fx.functions)
    dead = []
    for fx in files:
        for node, name, cls, brace, _end, _values in fx.functions:
            if seen[fx.lang][name] - defined[fx.lang][name] <= 0 and not _live_by_rule(fx, name, cls, brace, is_entry):
                dead.append((node, _head_line(fx, brace), _public(fx, name, brace)))
    return sorted(dead)
