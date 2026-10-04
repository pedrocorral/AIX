"""Function heads of the brace languages: where a function starts, where its body is, what it is called.

FUNC_HEAD finds the heads by language; `head_body` says whether a match is a function and where its body's brace is
(a JS/TS head is read by a body finder: parameters skipped balanced, then a return type, then an arrow). For JS/TS,
`js_units` lists every function with a block body, callbacks included, `children_of` nests them, `blank_children`
removes a unit's nested functions from its own code and `context_label` names an anonymous one by its place."""
import re

KEYWORDS = set("""if else for while do return break continue switch case default try catch finally throw new delete
typeof instanceof in of function class extends import export from const let var async await yield this super null
true false undefined void fn let mut pub struct enum impl trait match loop use mod ref self Some None Ok Err
public private protected static final abstract interface package void int long double float boolean char byte short
""".split())
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`[^`]*`|\d+(?:\.\d+)?|[A-Za-z_]\w*|[^\sA-Za-z_0-9]')
JS_MODS = r"(?:(?:export|default|public|private|protected|static|readonly|override|abstract|async|declare)\s+)*"
GENERICS = r"(?:<(?:[^<>]|<[^<>]*>)*>\s*)?"   # `<Type extends Pick<IUser, 'id'>>`, one level nested, may span lines
FUNC_HEAD = {
    # function f( | const f[: Type] = [async] (params[: Ret]) => { | method(params)[: Ret] {   (params may nest one level of parens)
    "js": re.compile(
        # an assignment: `const f = (`, `app.init = function init(`, `module.exports = function (`, `private onUnload = async (`, `x => {`
        r"^[ \t]*" + JS_MODS + r"(?:(?:const|let|var)\s+)?(?:module\.exports|(?:[\w$]+\.)*(?P<target>[\w$]+))\s*(?::\s*[^=\n]*?)?\s*=\s*(?:async\s+)?"
        r"(?:function\s*\*?\s*(?P<own>\w+)?\s*" + GENERICS + r"\(|" + GENERICS + r"\(|(?P<single>\w+)\s*=>)"
        # an object-literal member: `html: function () {`, `next: () => {`, `'key': async (`
        r"|^[ \t]*(?P<key>[\w$]+|'[^'\n]*'|\"[^\"\n]*\")\s*:\s*(?:async\s+)?(?:function\s*\*?\s*(?P<own2>\w+)?\s*" + GENERICS + r"\(|" + GENERICS + r"\(|(?P<single2>\w+)\s*=>)"
        # a declaration or a named function expression anywhere: `function f(`, `return function expressInit(`
        r"|\bfunction\s*\*?\s*(?P<decl>\w+)\s*" + GENERICS + r"\("
        # an accessor, then a method (or a call at line start: js_body tells them apart)
        r"|^[ \t]*(?:static\s+)?(?:get|set)\s+(?P<accessor>\w+)\s*\("
        r"|^[ \t]*" + JS_MODS + r"(?:\*\s*)?(?P<method>[\w$]+)\s*" + GENERICS + r"\(", re.M),
    "rust": re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+(\w+)", re.M),
    "java": re.compile(r"^[ \t]*(?:(?:public|private|protected|static|final|abstract|synchronized|default|native|@[\w.]+(?:\([^()\n]*\))?)[ \t]+)*(?:<[^>\n]*>[ \t]+)?(?:[\w$.]+(?:<[^>\n]*>)?(?:\[\])*[ \t]+)?(\w+)[ \t]*\((?:[^()]|\([^()]*\))*\)\s*(?:throws\s+[\w.,\s]+?)?\s*\{", re.M)   # no ambiguous `\s` overlaps: linear on an 8 KB file,
}


def _close_group(text: str, i: int, lang: str = "js") -> int:
    """Index of the bracket closing the one at `i` (`(`, `[`, `{` or `<`), strings, comments and (JS) regex literals
    skipped; -1 if none."""
    opener, closer = text[i], {"(": ")", "[": "]", "{": "}", "<": ">"}[text[i]]
    skip = SKIP_JS if lang == "js" else SKIP_TOKEN
    depth, j = 0, i
    while j < len(text):
        m = skip.match(text, j)
        if m:
            j = m.end(); continue
        depth += (text[j] == opener) - (text[j] == closer)
        if depth == 0:
            return j
        j += 1
    return -1


def _skip_blank(text: str, j: int, newlines: bool) -> int:
    while j < len(text) and text[j] in (" \t\r\n" if newlines else " \t"):
        j += 1
    return j


def _skip_type(text: str, j: int) -> int:
    """Past a TypeScript type annotation starting at `j`: words, unions, balanced groups; a `{` after the first token
    is the body, a line end after a complete type ends it (an interface member), `=>` ends it (an arrow follows)."""
    first, after_op = True, False
    while j < len(text):
        j = _skip_blank(text, j, False)
        if text[j:j + 1] == "\n":
            k = _skip_blank(text, j, True)
            if not (text[k:k + 1] in "|&{" or text.startswith("=>", k)):
                return j
            j = k; continue
        if _type_ends(text, j, first, after_op):
            return j
        j, first, after_op = _type_token(text, j, first)
    return j


def _type_ends(text: str, j: int, first: bool, after_op: bool) -> bool:
    c = text[j:j + 1]
    body = c == "{" and not first and not after_op
    return text.startswith("=>", j) or body or not (c in "<([{|&?" or c.isalnum() or c in "_$.'\"")


def _type_token(text: str, j: int, first: bool) -> tuple:
    """One token of a type at `j`, a balanced group, an operator or a word: (index after it, first, after_op)."""
    c = text[j]
    if c in "<([{":
        end = _close_group(text, j)
        return (end + 1 if end >= 0 else len(text)), False, False
    if c in "|&?":
        return j + 1, first, True
    k = j + 1
    while k < len(text) and (text[k].isalnum() or text[k] in "_$."):
        k += 1
    return k, False, False


def js_body(text: str, end: int, arrow: bool = False) -> int:
    """Index of the body's `{` for a JS/TS head whose match ends at its `(` or `=>`: the parameters are skipped
    balanced (a destructured pattern or an inline type may hold braces), then a return type, then an arrow. A `;`,
    a line end or anything else first means no body: a signature, a call, a plain assignment. `arrow` demands the
    `=>` (an anonymous arrow function read from its `(`)."""
    j = end
    if text[end - 1] == "(":
        j = _close_group(text, end - 1)
        if j < 0:
            return -1
        j += 1
    j = _skip_blank(text, j, True)
    if text.startswith(":", j):
        j = _skip_blank(text, _skip_type(text, j + 1), True)
    if text.startswith("=>", j):
        j = _skip_blank(text, j + 2, True)
        if not text.startswith("{", j) and not arrow:
            j = _skip_blank(text, _skip_type(text, j), True)   # `): (event: PointerEvent) => void {`: a function type returned
    elif arrow:
        return -1
    return j if text.startswith("{", j) else -1


def _js_name(m) -> str:
    g = m.groupdict()
    return g["own"] or g["own2"] or g["decl"] or g["accessor"] or g["target"] or g["method"] or (g["key"] or "").strip("'\"") or None


def _in_comment(text: str, pos: int) -> bool:
    line = text[text.rfind("\n", 0, pos) + 1:pos]
    return "//" in line or line.lstrip().startswith(("*", "/*"))


def _js_head_body(text: str, m):
    name = _js_name(m)
    keyword = name in KEYWORDS and not (m.group("method") and name in ("delete", "default"))   # `delete(id) {` is a method
    if not name or keyword or (m.group("decl") and _in_comment(text, m.start())):
        return None
    brace = js_body(text, m.end())
    return (name, brace) if brace >= 0 else None


def head_body(text: str, m, lang: str):
    """(name, index of the body's `{`) for a FUNC_HEAD match, or None when it is not a function: a keyword
    (`if (`), a JS signature or call, a Java or Rust declaration (`;` before the brace)."""
    if lang == "js":
        return _js_head_body(text, m)
    name = next((g for g in m.groups() if g), None)
    brace = text.find("{", m.end() - 1)
    if not name or (lang != "rust" and name in KEYWORDS) or brace < 0 or ";" in text[m.end() - 1:brace]:
        return None   # `;` first: a declaration (a Java interface method, a Rust trait method)
    return name, brace


ANON_FUNCTION = re.compile(r"\bfunction\s*\*?\s*" + GENERICS + r"\(")                                   # `function (req, res) {`
SINGLE_ARROW = re.compile(r"(?<![\w$.])(?:async\s+)?([\w$]+)\s*=>\s*\{")                 # `x => {`
CALLEE = re.compile(r"([\w$.]+)\s*(?:<[^<>\n]*>)?\s*\(\s*(?:(['\"])((?:\\.|(?!\2)[^\\\n])*)\2\s*,)?\s*(?:async\s+)?$", re.S)   # `app.get('/users', ` before the head
DEFAULT_EXPORT = re.compile(r"export\s+default\s*(?:async\s+)?$")
PROP = re.compile(r"(\w+)\s*=\s*\{\s*$")                                                   # JSX `onClick={` before the head


def js_units(text: str) -> list:
    """Every JS/TS function with a block body, named or not: (name or None, head start, brace index, end index),
    sorted by position. A named head wins over the anonymous reading of the same brace; an empty anonymous body
    (`.catch(() => {})`) stays in its parent."""
    units = {}
    for m in FUNC_HEAD["js"].finditer(text):
        hb = head_body(text, m, "js")
        if hb:
            units.setdefault(hb[1], (hb[0], m.start()))
    for start, brace in _anonymous_heads(text):
        units.setdefault(brace, (None, start))
    out = [(name, start, brace, _close_group(text, brace)) for brace, (name, start) in sorted(units.items())]
    return [u for u in out if u[3] > 0 and (u[0] or text[u[2] + 1:u[3]].strip())]


def _anonymous_heads(text: str) -> list:
    """(head start, brace) of every `function (`, `(…) => {` and `x => {` with a block body."""
    out = [(m.start(), js_body(text, m.end())) for m in ANON_FUNCTION.finditer(text)]
    out += [(m.start(), js_body(text, m.end(), arrow=True)) for m in re.finditer(r"\(", text)]
    out += [(m.start(), m.end() - 1) for m in SINGLE_ARROW.finditer(text)]
    return [(start, brace) for start, brace in out if brace >= 0]


def children_of(units: list) -> dict:
    """brace -> the (brace, end) spans of the functions directly inside each unit."""
    out, stack = {u[2]: [] for u in units}, []
    for _, _, brace, end in units:
        while stack and stack[-1][1] < brace:
            stack.pop()
        if stack:
            out[stack[-1][0]].append((brace, end))
        stack.append((brace, end))
    return out


def blank_children(body: str, brace: int, children: list) -> str:
    """The body with each child's text (braces included) replaced by blanks, newlines kept: the unit's own code."""
    for cb, ce in children:
        a, b = cb - brace, ce - brace + 1
        body = body[:a] + re.sub(r"[^\n]", " ", body[a:b]) + body[b:]
    return body


def context_label(text: str, start: int) -> str:
    """What an anonymous function is passed to or assigned to: `app.get('/users') callback`, `onClick prop`."""
    before = text[max(0, text.rfind("\n", 0, start) - 400):start]
    m = CALLEE.search(before)
    if m and m.group(1).strip(".") not in KEYWORDS:
        callee = m.group(1).strip(".")
        return f"{callee}({m.group(2)}{m.group(3)[:30]}{m.group(2)}) callback" if m.group(3) is not None else f"{callee} callback"
    m = PROP.search(before)
    return f"{m.group(1)} prop" if m else "default export" if DEFAULT_EXPORT.search(before) else "anonymous function"


SKIP_TOKEN = re.compile(r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n]){1,3}'|`(?:[^`\\]|\\.)*`|\br#*\"[^\"]*\"#*", re.S)
REGEX_LITERAL = r"/(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^/\\\n\[])+/[a-z]*"   # `/\{(.+)\}/g`: braces and parens inside are not code
SKIP_JS = re.compile(r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'|`(?:[^`\\]|\\.)*`|(?<=[(,=:\[!&|?{};])" + REGEX_LITERAL + r"|(?<=[(,=:\[!&|?{};] )" + REGEX_LITERAL, re.S)
# what a brace inside cannot open or close: comments, strings, char literals (`'a'`, not a Rust lifetime), template literals, raw strings


def brace_block(text: str, start: int, lang: str = "") -> str:
    """Text from the first '{' at/after `start` to its matching '}', braces inside strings and comments ignored
    (and inside regex literals and full single-quoted strings for JS/TS)."""
    i = text.find("{", start)
    if i < 0:
        return ""
    skip = SKIP_JS if lang == "js" else SKIP_TOKEN
    depth, j = 0, i
    while j < len(text):
        m = skip.match(text, j)
        if m:
            j = m.end(); continue
        depth += (text[j] == "{") - (text[j] == "}")
        if depth == 0:
            return text[i:j + 1]
        j += 1
    return text[i:]
