"""Leaf: the edges of one Rust file, resolved to project files. Comments are taken out first. Read: `mod x;` (the
child module's file), every path of a `use` tree (`use crate::{a, b::{c, self}};` is four paths, `as` aliases and
`*` globs included), and every path written in the code itself (`crate::billing::charge()`). A path resolves from
`crate`, `super` (the parent of the file's own module, so `src/a/b.rs` -> `crate::a`), `self`, a child module of the
file's module (Rust 2018 lets `use orders::x` name it), or another crate of the same Cargo workspace by its name
(`grep_searcher::Searcher` -> that crate's `src/lib.rs`, then the module path inside it). External crates are no edge."""
import os, re
from pathlib import Path

from bracecomments import strip_strings
from codefiles import ROOT, SKIP

USE = re.compile(r"\b(?:pub(?:\([^)]*\))?\s+)?use\s+([^;]+);")
PUB_USE = re.compile(r"\bpub(?:\([^)]*\))?\s+use\s+([^;]+);")
EXTERN = re.compile(r"\bextern\s+crate\s+(\w+)")   # `pub extern crate grep_cli as cli;`: the whole crate, re-exported
MOD = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+(\w+)\s*;", re.M)
INLINE_MOD = re.compile(r"\bmod\s+(\w+)\s*\{")
TEST_MOD = re.compile(r"#\[cfg\(test\)\]\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+\w+\s*\{")
PATH = re.compile(r"(?<![\w:])((?:crate|super|self|[a-z_]\w*)(?:::\w+)+)")
_CRATES = {}   # ROOT -> {crate name with underscores: the folder of its library's root file}
_ROOTS = {}    # ROOT -> {folder of a crate root file: that file}
_ALL_ROOT_FILES = {}   # ROOT -> every crate root file (a folder may hold several: src/lib.rs and src/main.rs, tests/*.rs) (src/lib.rs, src/main.rs, src/bin/*.rs, `path =` in Cargo.toml)
TOML_PATH = re.compile(r'^\s*path\s*=\s*"([^"]+\.rs)"', re.M)
_REEXPORTS = {}   # file -> {name it re-exports: the path segments it names}
_SCOPES = {}      # file -> {every name its use declarations and `mod` lines bind: the path segments}
IDENT = re.compile(r"\b[A-Za-z_]\w*\b")
DEFINES = re.compile(r"\b(?:fn|struct|enum|trait|type|const|static|union)\s+([A-Za-z_]\w*)|\bmacro_rules!\s*([A-Za-z_]\w*)")
_DEFS, _GLOBS = {}, {}   # file -> names it defines; file -> the files it glob-imports
GLOB_DEPTH = 2
REEXPORT_DEPTH = 3


def _scan():
    """Every Cargo.toml of the project, top-down (the shallowest wins over a fixture of the same name): the crates
    by name and the crate root files, wherever `path =` puts them (ripgrep's binary is crates/core/main.rs)."""
    crates, roots, every = {}, {}, set()
    for folder, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in SKIP and not d.startswith(".")]   # never into target/ or node_modules/
        if "Cargo.toml" in files:
            every |= _read_toml(Path(folder).resolve(), crates, roots)
    _CRATES[ROOT], _ROOTS[ROOT], _ALL_ROOT_FILES[ROOT] = crates, roots, every


def _root_candidates(folder: Path, text: str) -> list:
    """Every file Cargo may compile as a crate root: lib, main, bins, tests, examples, benches, `path = ...`."""
    files = [folder / "src" / "lib.rs", folder / "src" / "main.rs", *sorted((folder / "src" / "bin").glob("*.rs"))]
    files += [f for sub in ("tests", "examples", "benches") for f in sorted((folder / sub).glob("*.rs"))]   # each its own crate
    return files + [(folder / p).resolve() for p in TOML_PATH.findall(text)]


def _read_toml(folder: Path, crates: dict, roots: dict):
    text = (folder / "Cargo.toml").read_text(encoding="utf-8", errors="replace")
    files = _root_candidates(folder, text)
    present = [f.resolve() for f in files if f.is_file()]
    for f in present:
        roots.setdefault(f.parent, f)   # lib.rs first: a folder holding both is the library's
    name = re.search(r'^\[package\](?:(?!^\[).)*?^name\s*=\s*"([^"]+)"', text, re.M | re.S)
    lib = next((f for f in files if f.is_file() and f.name == "lib.rs"), None)
    if name:
        crates.setdefault(name.group(1).replace("-", "_"), (lib.parent if lib else folder / "src"))
    return set(present)


def workspace_crates() -> dict:
    """crate name (dashes as underscores) -> the folder of its library root, for every Cargo.toml [package]."""
    if ROOT not in _CRATES:
        _scan()
    return _CRATES[ROOT]


def crate_root_dir(f: Path) -> Path:
    """The folder of the root file of the crate a file belongs to: the deepest such folder above it (src/ as a rule;
    a `path =` of Cargo.toml elsewhere)."""
    if ROOT not in _ROOTS:
        _scan()
    f = f.resolve()
    above = [d for d in _ROOTS[ROOT] if d == f.parent or d in f.parents]
    if above:
        return max(above, key=lambda d: len(d.parts))
    crate = next((p for p in f.parents if (p / "Cargo.toml").exists()), f.parent)
    return crate / "src"


def expand_use_named(tree: str) -> list:
    """(path, the name it binds) per leaf of a use tree: `a::{b as c, d}` -> [('a::b', 'c'), ('a::d', 'd')]."""
    tree = re.sub(r"\s*([{},]|::)\s*", r"\1", tree.strip())
    if "{" not in tree:
        return [_leaf(tree)]
    brace = tree.index("{")
    prefix, inner = tree[:brace].rstrip(":"), tree[brace + 1:_closing(tree, brace)]
    out = [_joined(prefix, p, name) for part in _split_top(inner) for p, name in expand_use_named(part)]
    return [(p, n) for p, n in out if p]


def _joined(prefix: str, path: str, name: str) -> tuple:
    """A leaf of a `{...}` group put after its prefix; `self` names the prefix itself, `*` globs it."""
    if path in ("self", "*"):
        return prefix, prefix.split("::")[-1] if path == "self" else name
    return (f"{prefix}::{path}" if prefix else path), name


def _leaf(path: str) -> tuple:
    """One leaf without its alias and glob: `a::b as c` -> ('a::b', 'c'), `a::*` -> ('a', '*')."""
    parts = re.split(r"\s+as\s+", path.strip(), maxsplit=1)
    original, alias = parts[0], (parts[1].strip() if len(parts) > 1 else "")
    clean = re.sub(r"(::\*|::self)$", "", original)
    return clean, alias or ("*" if original.endswith("::*") else clean.split("::")[-1])


def _closing(s: str, i: int) -> int:
    depth = 0
    for j in range(i, len(s)):
        depth += {"{": 1, "}": -1}.get(s[j], 0)
        if depth == 0:
            return j
    return len(s)


def _split_top(s: str) -> list:
    parts, depth, cur = [], 0, ""
    for ch in s:
        if ch == "," and depth == 0:
            parts.append(cur); cur = ""
            continue
        depth += {"{": 1, "}": -1}.get(ch, 0)
        cur += ch
    return [p for p in parts + [cur] if p]


# ---- modules and files --------------------------------------------------------------------------------------------

def module_path(f: Path, src: Path) -> list:
    """The module path of a file inside its crate: src/lib.rs -> [], src/a/mod.rs -> ['a'], src/a/b.rs -> ['a', 'b']."""
    try:
        parts = list(f.resolve().relative_to(src.resolve()).parts)
    except ValueError:
        return []
    if parts and parts[-1] in ("mod.rs",) or (len(parts) == 1 and parts[0] in ("lib.rs", "main.rs")) or _crate_root(src) == f.resolve():
        return parts[:-1]
    if parts and parts[0] == "bin":
        return []
    return parts[:-1] + [Path(parts[-1]).stem] if parts else []


def module_file(src: Path, path: list):
    """The file of the longest prefix of `path` that is a module of the crate (a.rs or a/mod.rs), else None."""
    return _module_prefix(src, path)[0]


def _module_prefix(src: Path, path: list) -> tuple:
    """(file, segments it consumed) for the longest prefix of `path` that is a module file, else (None, 0)."""
    for n in range(len(path), 0, -1):
        base = src.joinpath(*path[:n])
        hit = next((c for c in (base.with_suffix(".rs"), base / "mod.rs") if c.is_file()), None)
        if hit:
            return hit, n
    return None, 0


def _reexports(f: Path) -> dict:
    """name -> path segments, for every `pub use` of a file: `pub use wrapping::WrappingMode;` re-exports a name."""
    if f not in _REEXPORTS:
        code = strip_strings(f.read_text(encoding="utf-8", errors="replace"), "rust")
        _REEXPORTS[f] = {name: path.split("::") for u in PUB_USE.finditer(code) for path, name in expand_use_named(u.group(1)) if name != "*"}
    return _REEXPORTS[f]


def _locate(src: Path, full: list, depth: int):
    """The file defining `full` (a module path in the crate at src): the deepest module file, then through the
    `pub use` that re-exports the first name left over (`crate::WrappingMode` -> wrapping.rs, not lib.rs)."""
    f, n = _module_prefix(src, full)
    if f is None:
        f, n = _crate_root(src), 0
    left = full[n:]
    target = _reexports(f).get(left[0]) if f is not None and left and depth < REEXPORT_DEPTH else None
    hit = resolve(target, f, src, (), depth + 1) if target else None
    return hit or f


def _crate_root(src: Path):
    """The root file of the crate whose root folder is src."""
    if ROOT not in _ROOTS:
        _scan()
    return _ROOTS[ROOT].get(src.resolve()) or next((c for c in (src / "lib.rs", src / "main.rs") if c.is_file()), None)


def resolve(segments: list, f: Path, src: Path, inline: list = (), depth: int = 0):
    """The project file a path names from file f (inside the inline modules `inline` of it, `mod tests { ... }`),
    or None when it is external or unknown."""
    head, rest, here = segments[0], segments[1:], module_path(f, src) + list(inline)
    if head in ("crate", "super", "self"):
        full = _anchored(head, rest, here)
        return _locate(src, full, depth) if full is not None else None
    if _module_prefix(src, here + [head])[1] == len(here) + 1:   # exactly a child module, not a shorter prefix
        return _locate(src, here + segments, depth)
    other = workspace_crates().get(head)
    if other is None or (other == src.resolve() and not _is_root_file(f)):
        return None   # a module of the library names its own crate `crate::`, never by name
    return _locate(other, rest, depth)


def _is_root_file(f: Path) -> bool:
    """A crate root of its own (a binary, an integration test, an example): it names its library by the crate name."""
    if ROOT not in _ROOTS:
        _scan()
    return f.resolve() in _ALL_ROOT_FILES[ROOT]


def _anchored(head: str, rest: list, here: list):
    """The module path inside the crate that a `crate::`, `super::` or `self::` path names (None for a bare `crate`)."""
    if head == "crate":
        return rest or None
    if head == "self":
        return here + rest
    up = here[:-1]
    while rest and rest[0] == "super":
        up, rest = up[:-1], rest[1:]
    return up + rest


def _inline_regions(code: str) -> list:
    """(open brace, close brace, name) of every inline `mod name { ... }` block of a file."""
    return [(m.end() - 1, _closing(code, m.end() - 1), m.group(1)) for m in INLINE_MOD.finditer(code)]


def _inline_at(regions: list, pos: int) -> list:
    """The inline modules enclosing a position, outermost first: `super` inside `mod tests {}` is the file's module."""
    return [name for start, end, name in sorted(regions) if start < pos < end]


def _paths(code: str) -> list:
    """(position, path, name bound) of every use-tree leaf, and (position, path, None) of every path in the code."""
    found = [(u.start(), p, n) for u in USE.finditer(code) for p, n in expand_use_named(u.group(1))]
    found += [(m.start(), m.group(1), None) for m in EXTERN.finditer(code)]
    blanked = USE.sub(lambda u: " " * len(u.group(0)), code)   # same length: positions still match the regions
    return found + [(m.start(), m.group(1), None) for m in PATH.finditer(blanked)]


def _scope(f: Path) -> dict:
    """name -> path segments for every name a file's `use` declarations (private ones too) and `mod x;` lines bind:
    what `use that::module::*` brings into a child module."""
    if f not in _SCOPES:
        code = _code(f)
        scope = {m.group(1): ["self", m.group(1)] for m in MOD.finditer(code)}
        scope.update({n: p.split("::") for u in USE.finditer(code) for p, n in expand_use_named(u.group(1)) if n != "*"})
        _SCOPES[f] = scope
    return _SCOPES[f]


def _code(f: Path) -> str:
    return strip_strings(f.read_text(encoding="utf-8", errors="replace"), "rust")


def _defs(f: Path) -> set:
    """The names a file defines (fn, struct, enum, trait, type, const, static, union, macro_rules!)."""
    if f not in _DEFS:
        _DEFS[f] = {a or b for a, b in DEFINES.findall(_code(f))}
    return _DEFS[f]


def _glob_files(f: Path) -> list:
    """The files a file glob-imports (`use crate::error::*;`)."""
    if f not in _GLOBS:
        _GLOBS[f] = []   # a glob cycle stops here
        code, src = _code(f), crate_root_dir(f)
        regions = _inline_regions(code)
        leaves = [(u.start(), p) for u in USE.finditer(code) for p, n in expand_use_named(u.group(1)) if n == "*"]
        hits = (resolve(p.lstrip(":").split("::"), f, src, _inline_at(regions, pos), 1) for pos, p in leaves)
        _GLOBS[f] = [h for h in hits if h and h != f]
    return _GLOBS[f]


def _glob_targets(module: Path, names: tuple, depth: int = 0) -> list:
    """The files behind the names a file takes from `use module::*` and writes: what the module imports by name,
    then (two globs deep) the files it glob-imports that define the rest. `names` is (every identifier, the ones
    written as a path head `x::`): a module name counts only as a path head, never as a variable of that name."""
    idents, heads = names
    scope, src = _scope(module), crate_root_dir(module)
    bound = {n for n in idents & scope.keys() if scope[n] != ["self", n] or n in heads}
    out = [resolve(scope[n], module, src, (), 1) for n in sorted(bound)]
    rest = idents - scope.keys() - _defs(module)
    for g in (_glob_files(module) if depth < GLOB_DEPTH and rest else []):
        found = rest & _defs(g)
        out += ([g] if found else []) + _glob_targets(g, (rest - found, heads), depth + 1)
    return out


def _without_tests(code: str) -> str:
    """The code with every `#[cfg(test)] mod x { ... }` body blanked (same length): test code, like a test file, uses
    whatever it exercises and is no dependency of the crate."""
    for m in reversed(list(TEST_MOD.finditer(code))):
        end = _closing(code, m.end() - 1)
        code = code[:m.end()] + re.sub(r"[^\n]", " ", code[m.end():end]) + code[end:]
    return code


def rust_module_edges(f: Path, ownership: bool = True) -> list:
    """The files f uses; with `ownership` also the child modules it declares (`mod x;`): a crate needs those edges to
    reach its files (dead code), a boundary check does not (declaring a module is not using it). The body of a
    `#[cfg(test)]` module is left out."""
    code = _without_tests(strip_strings(f.read_text(encoding="utf-8", errors="replace"), "rust"))
    src, out, regions = crate_root_dir(f), [], _inline_regions(code)
    if ownership:
        out += [module_file(src, module_path(f, src) + _inline_at(regions, m.start()) + [m.group(1)]) for m in MOD.finditer(code)]
    plain = USE.sub(" ", code)
    names = (set(IDENT.findall(plain)), set(re.findall(r"\b([a-z_]\w*)::", plain)))
    for pos, p, bound in _paths(code):
        hit = resolve(p.lstrip(":").split("::"), f, src, _inline_at(regions, pos))
        globbed = bound == "*" and hit is not None and hit.resolve() != f.resolve()
        out += [hit] + (_glob_targets(hit, names) if globbed else [])
    return [h for h in out if h and h.resolve() != f.resolve()]
