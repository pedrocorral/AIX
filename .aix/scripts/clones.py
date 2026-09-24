"""`aix code clones`: exact clones (equal normalised structure) and near clones (Dice overlap of winnowed
k-gram fingerprints) among the functions of every supported language."""
import ast, re
from collections import defaultdict
from pathlib import Path

from codefiles import EXT, rel, source_files
from depedges import iter_functions


MIN_LINES, KGRAM, WINDOW, SIMILARITY = 6, 5, 4, 70
KEYWORDS = set("""if else for while do return break continue switch case default try catch finally throw new delete
typeof instanceof in of function class extends import export from const let var async await yield this super null
true false undefined void fn let mut pub struct enum impl trait match loop use mod ref self Some None Ok Err
public private protected static final abstract interface package void int long double float boolean char byte short
""".split())
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`[^`]*`|\d+(?:\.\d+)?|[A-Za-z_]\w*|[^\sA-Za-z_0-9]')
FUNC_HEAD = {
    # function f( | const f[: Type] = [async] (params[: Ret]) => { | method(params)[: Ret] {   (params may nest one level of parens)
    "js": re.compile(r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\s*\*?\s*(\w+)\s*\(|(?:const|let|var)\s+(\w+)\s*(?::\s*[^=]+?)?=\s*(?:async\s*)?(?:\((?:[^()]|\([^()]*\))*\)|\w+)\s*(?::\s*[^=]+?)?=>\s*\{|(?:public|private|protected|static|async|\s)*(\w+)\s*\((?:[^()]|\([^()]*\))*\)\s*(?::\s*[^{]+)?\{)", re.M | re.S),
    "rust": re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+(\w+)", re.M),
    "java": re.compile(r"^\s*(?:public|private|protected|static|final|abstract|synchronized|\s)*[\w<>\[\], ]+\s+(\w+)\s*\([^)]*\)\s*(?:throws[^{]+)?\{", re.M),
}


def _docless_body(fn) -> list:
    first = fn.body[0] if fn.body else None
    has_doc = isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant) and isinstance(first.value.value, str)
    return fn.body[1:] if has_doc else fn.body


LEAF_TOKENS = {ast.Name: "NAME", ast.arg: "ARG"}


def _normalise_node(node, out: list):
    """Append the structure token of a node (identifiers -> NAME/ATTR/ARG, literals -> their type) and recurse."""
    if isinstance(node, ast.Constant):
        out.append(type(node.value).__name__.upper())
        return
    if type(node) in LEAF_TOKENS:
        out.append(LEAF_TOKENS[type(node)])
        return
    attribute = isinstance(node, ast.Attribute)
    out.append("ATTR" if attribute else type(node).__name__)
    for child in ([node.value] if attribute else ast.iter_child_nodes(node)):
        _normalise_node(child, out)


def normalise_py(fn) -> list:
    """Structure tokens of a Python function: node kinds, with identifiers -> NAME/ATTR/ARG and literals -> their
    type, docstring dropped. Two functions with equal sequences are type-1/2 clones."""
    out = []
    for a in fn.args.args + fn.args.kwonlyargs:
        _normalise_node(a, out)
    for stmt in _docless_body(fn):
        _normalise_node(stmt, out)
    return out


def normalise_tokens(text: str) -> list:
    """Token normalisation for JS/TS/Rust/Java bodies: identifiers -> ID, numbers -> NUM, strings -> STR, keywords and
    punctuation kept. Comments stripped first."""
    text = re.sub(r"//[^\n]*|/\*.*?\*/", " ", text, flags=re.S)
    out = []
    for tok in TOKEN.findall(text):
        if tok[0] in "\"'`":
            out.append("STR")
        elif tok[0].isdigit():
            out.append("NUM")
        elif tok[0].isalpha() or tok[0] == "_":
            out.append(tok if tok in KEYWORDS else "ID")
        else:
            out.append(tok)
    return out


def brace_block(text: str, start: int) -> str:
    """Text from the first '{' at/after `start` to its matching '}'."""
    i = text.find("{", start)
    if i < 0:
        return ""
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
    return text[i:]


def _python_units(f: Path, text: str) -> list:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    out = []
    for cls, fn in iter_functions(tree):
        n_lines = (fn.end_lineno or fn.lineno) - fn.lineno + 1
        if n_lines >= MIN_LINES:
            out.append((f"{rel(f)}:{cls + '.' if cls else ''}{fn.name}", rel(f), fn.lineno, n_lines, normalise_py(fn)))
    return out


def _token_units(f: Path, text: str, lang: str) -> list:
    out = []
    for m in FUNC_HEAD[lang].finditer(text):
        name = next((g for g in m.groups() if g), "anon")
        if name in KEYWORDS:
            continue
        block = brace_block(text, m.end() - 1)
        n_lines = block.count("\n") + 1
        if n_lines >= MIN_LINES:
            out.append((f"{rel(f)}:{name}", rel(f), text.count("\n", 0, m.start()) + 1, n_lines, normalise_tokens(block)))
    return out


def functions_for_clones(roots):
    """(node name, file, line, n_lines, token sequence) for every function big enough to matter."""
    out = []
    for f in source_files(roots):
        lang = EXT[f.suffix]
        text = f.read_text(encoding="utf-8", errors="replace")
        out += _python_units(f, text) if lang == "python" else _token_units(f, text, lang)
    return out


def fingerprints(tokens) -> set:
    """Winnowing (Schleimer, Wilkerson & Aiken 2003): hash every k-gram, keep the minimum of each window."""
    if len(tokens) < KGRAM:
        return {hash(tuple(tokens))}
    grams = [hash(tuple(tokens[i:i + KGRAM])) for i in range(len(tokens) - KGRAM + 1)]
    if len(grams) <= WINDOW:
        return set(grams)
    return {min(grams[i:i + WINDOW]) for i in range(len(grams) - WINDOW + 1)}


def _sharing_index(prints: dict) -> dict:
    """fingerprint -> the functions carrying it."""
    index = defaultdict(set)
    for name, fp in prints.items():
        for h in fp:
            index[h].add(name)
    return index


def _dice(first: set, second: set) -> float:
    return 2 * len(first & second) / (len(first) + len(second)) * 100


def _candidate_pairs(prints: dict, in_exact: set):
    """Every unordered pair of functions sharing a fingerprint, once, skipping pairs already in an exact group."""
    index = _sharing_index(prints)
    seen = set()
    for name, fp in prints.items():
        for other in {o for h in fp for o in index[h] if o != name}:
            pair = tuple(sorted((name, other)))
            if pair not in seen and not (name in in_exact and other in in_exact):
                seen.add(pair)
                yield pair


def _near_pairs(funcs, prints: dict, in_exact: set, similarity: float) -> list:
    info = {fx[0]: fx for fx in funcs}
    near = []
    for first, second in _candidate_pairs(prints, in_exact):
        dice = _dice(prints[first], prints[second])
        if dice >= similarity:
            near.append((dice, info[first], info[second]))
    return near


def find_clones(funcs, similarity):
    """Exact groups (equal normalised sequences) and near pairs (Dice overlap of fingerprints >= similarity %)."""
    by_hash = defaultdict(list)
    for fx in funcs:
        by_hash[hash(tuple(fx[4]))].append(fx)
    exact = [g for g in by_hash.values() if len(g) > 1]
    in_exact = {fx[0] for g in exact for fx in g}
    prints = {fx[0]: fingerprints(fx[4]) for fx in funcs}
    near = _near_pairs(funcs, prints, in_exact, similarity)
    exact.sort(key=lambda g: -len(g) * g[0][3])
    near.sort(key=lambda x: -(x[0] * min(x[1][3], x[2][3])))
    return exact, near


def render_clones(roots, similarity):
    funcs = functions_for_clones(roots)
    exact, near = find_clones(funcs, similarity)
    lines = [f"Clones — {', '.join(roots)}", "",
             f"  functions analysed {len(funcs)} (>= {MIN_LINES} lines); exact clone groups {len(exact)} (types 1-2: same structure, names and literals may differ); near-clones {len(near)} (type 3: >= {similarity:g} % shared fingerprints, winnowing k={KGRAM})", ""]
    for g in exact[:20]:
        lines.append(f"  EXACT  {len(g)} × ~{g[0][3]} lines: " + ", ".join(f"{fx[0]} (l.{fx[2]})" for fx in g) + "   -> keep one, make it a leaf")
    for dice, a, b in near[:30]:
        lines.append(f"  NEAR   {dice:3.0f} %  {a[0]} (l.{a[2]}, {a[3]} lines)  ~  {b[0]} (l.{b[2]}, {b[3]} lines)   -> extract the shared part into a leaf")
    lines.append("  Every line is a candidate: two functions may legitimately share a shape (adapters of one port); merge only when they share a purpose. Fix with: skill refactor-clone")
    return "\n".join(lines), len(exact)
