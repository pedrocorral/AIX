"""Leaf: taint analysis of JavaScript/TypeScript files without a parser. Statement by statement (a statement may
span lines until its parentheses close), scoped by brace depth: input sources (Express/Koa/Fastify/Next request
objects, process.env/argv, location, URLSearchParams, formData) flow through assignments, destructuring, template
literals and concatenation; a sink reached without a sanitiser is a finding; local functions are followed one call
deep. Evidence to review, not proof: no types, no middleware, no cross-file."""
import re
from pathlib import Path

from codefiles import ROOT, rel, source_files
from securityrules import ACCEPT, ADVICE, SKIP_FILE, MARKER_LINES

JS_EXT = (".js", ".jsx", ".ts", ".tsx", ".mjs")
SOURCES = re.compile(r"\breq(?:uest)?\.(?:query|params|body|headers|cookies|url|originalUrl|nextUrl)\b|\bctx\.(?:request\.)?(?:query|params|body|headers)\b"
                     r"|\bprocess\.(?:env|argv|stdin)\b|\bsearchParams\.get\(|\blocation\.(?:search|hash|href|pathname)\b|\bnew URLSearchParams\("
                     r"|\bformData\.get\(|\bdocument\.(?:cookie|referrer)\b|\breq(?:uest)?\.(?:json|text|formData)\(\)|\bwindow\.name\b")
SANITISED = re.compile(r"(?:Number|parseInt|parseFloat|Boolean|encodeURIComponent|encodeURI|escape|escapeHtml|sanitize|quote|basename|validator\.escape|"
                       r"DOMPurify\.sanitize|path\.basename|shellQuote\.quote|shell\.quote)\((?:[^()]|\([^()]*\))*\)")
IDENT = re.compile(r"[A-Za-z_$][\w$]*")
SINKS = [  # (call head, VUL row, CWE, kind, which argument is dangerous)
    (r"\b(?:child_process\.)?exec(?:Sync)?\(", "VUL-INJ-002", "CWE-78", "shell command", "any"),
    (r"\b(?:child_process\.)?(?:spawn|spawnSync|execFile|execFileSync)\(", "VUL-INJ-002", "CWE-78", "shell command", "shell"),
    (r"\beval\(|\bnew Function\(", "VUL-INJ-002", "CWE-95", "eval", "any"),
    (r"\bset(?:Timeout|Interval)\(", "VUL-INJ-002", "CWE-95", "eval", "string"),
    (r"\bfs(?:\.promises)?\.\w+\(|(?<![\w.$])(?:readFile|writeFile|appendFile|readdir|unlink|rm|stat|access|open|createReadStream|createWriteStream)(?:Sync)?\(|\b\w+\.(?:sendFile|download)\(",
     "VUL-INJ-002", "CWE-22", "file path", "first"),
    (r"\b\w+\.(?:query|raw|execute|\$queryRawUnsafe|\$executeRawUnsafe)\(", "VUL-INJ-001", "CWE-89", "SQL statement", "assembled"),
    (r"\b\w+\.redirect\(|(?<![\w.])redirect\(|\bwindow\.open\(|\blocation\.(?:assign|replace)\(", "VUL-WEB-003", "CWE-601", "redirect target", "first"),
    (r"\b\w+\.insertAdjacentHTML\(|\bdocument\.write(?:ln)?\(|\b\w+\.html\(", "VUL-WEB-001", "CWE-79", "HTML sink", "any"),
    (r"\b\w+\.send\(", "VUL-WEB-001", "CWE-79", "HTML response", "assembled"),
    (r"(?<![\w.])fetch\(|\baxios(?:\.\w+)?\(|\bhttps?\.(?:get|request)\(|(?<![\w.])got\(", "VUL-INPUT-001", "CWE-918", "outbound request URL", "first"),
]
ASSIGN_SINKS = [(r"\.(?:innerHTML|outerHTML)\s*=(?!=)", "VUL-WEB-001", "CWE-79", "HTML sink"),
                (r"\b(?:window\.|document\.)?location(?:\.href)?\s*=(?!=)", "VUL-WEB-003", "CWE-601", "redirect target")]
JSX_SINK = re.compile(r"dangerouslySetInnerHTML=\{\{\s*__html:\s*([^}]+)\}")
ASSIGN = re.compile(r"^\s*(?:export\s+)?(?:(?:const|let|var)\s+)?(?:\{([^}]+)\}|([\w$]+))(?::\s*[^=]+?)?\s*=(?!=)\s*(.+?);?\s*$", re.S)
LOOP = re.compile(r"\bfor\s*\(\s*(?:const|let|var)\s+([\w$]+)\s+(?:of|in)\s+(.+?)\)")
FUNC = re.compile(r"(?:^|\n)\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?(?:function\s+([\w$]+)\s*\(([^)]*)\)|(?:const|let|var)\s+([\w$]+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*(?::[^=]+)?=>)")
COMMENTS = re.compile(r"//[^\n]*|/\*.*?\*/", re.S)


def _statements(lines: list, first: int = 1) -> list:
    """(line number, text) per statement: a line is joined with the next ones while its parentheses stay open and it
    did not open a block (`(req, res) => {` starts a handler, its lines are statements of their own)."""
    out, i = [], 0
    while i < len(lines):
        text, j = lines[i], i
        while text.count("(") > text.count(")") and not text.rstrip().endswith("{") and j + 1 < len(lines) and j - i < 12:
            j += 1; text += "\n" + lines[j]
        out.append((first + i, text)); i = j + 1
    return out


STRINGS = re.compile(r"`(?:[^`\\]|\\.)*`|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", re.S)


def _code_only(expr: str) -> str:
    """The expression without the text of its string literals; a template literal keeps its `${...}` parts."""
    return STRINGS.sub(lambda m: " ".join(re.findall(r"\$\{([^}]*)\}", m.group(0))) if m.group(0).startswith("`") else '""', expr)


def _args_of(text: str, start: int) -> list:
    """The top-level arguments of the call whose `(` is at text[start - 1]."""
    depth, args, cur = 0, [], ""
    for ch in text[start:]:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            if depth == 0:
                break
            depth -= 1
        if ch == "," and depth == 0:
            args.append(cur); cur = ""; continue
        cur += ch
    return [a.strip() for a in args + [cur] if a.strip()]


def _names_of(destructured: str) -> list:
    """`{ a, b: c = 1 }` -> [a, c]."""
    names = []
    for part in destructured.split(","):
        part = part.split("=")[0]
        names.append((part.split(":")[-1] if ":" in part else part).strip())
    return [n for n in names if n]


class _Taint:
    """A tainted variable: where the input came from, the brace depth it lives at, whether it was assembled (`+`, `${`)."""
    def __init__(self, source: str, depth: int, assembled: bool):
        self.source, self.depth, self.assembled = source, depth, assembled


class _Walk:
    """One pass over statements, with the tainted variables in scope, collecting sink hits."""
    def __init__(self, file: Path, lines: list, funcs: dict, findings: list, follow: bool = True):
        self.file, self.lines, self.funcs, self.findings, self.follow = file, lines, funcs, findings, follow
        self.tainted, self.depth = {}, 0

    def run(self, statements: list, initial: dict = None):
        self.tainted = {k: _Taint(v, 0, False) for k, v in (initial or {}).items()}
        for lineno, raw in statements:
            text = COMMENTS.sub(" ", raw)
            self._assignments(text, lineno)
            self._sinks(text, raw, lineno)
            if self.follow:
                self._calls(text)
            self._leave_scope(text)

    def taint_of(self, expr: str):
        """(source description, assembled) of an expression, or (None, False); sanitiser calls count as clean."""
        clean = SANITISED.sub("SAFE", _code_only(expr))
        m = SOURCES.search(clean)
        assembled = "${" in expr or "+" in clean
        if m:
            return m.group(0), assembled
        for name in IDENT.findall(clean):
            if name in self.tainted:
                return self.tainted[name].source, assembled or self.tainted[name].assembled
        return None, False

    def _assignments(self, text: str, lineno: int):
        m = LOOP.search(text)
        if m:
            self._bind([m.group(1)], m.group(2), lineno); return
        m = ASSIGN.match(text)
        if not m or (m.group(2) and "." in m.group(2)):
            return
        self._bind(_names_of(m.group(1)) if m.group(1) else [m.group(2)], m.group(3), lineno)

    def _bind(self, names: list, expr: str, lineno: int):
        source, assembled = self.taint_of(expr)
        for name in names:
            if source:
                self.tainted[name] = _Taint(f"{name} = ... from {source} (line {lineno})", self.depth, assembled)
            else:
                self.tainted.pop(name, None)

    def _sinks(self, text: str, raw: str, lineno: int):
        for head, vul, cwe, kind, which in SINKS:
            for m in re.finditer(head, text):
                self._check_call(text, m, (vul, cwe, kind, which), raw, lineno)
        for rx, vul, cwe, kind in ASSIGN_SINKS:
            m = re.search(rx, text)
            if m:
                self._report(text[m.end():], (vul, cwe, kind), raw, lineno + text.count("\n", 0, m.start()), text[m.start():m.end()].strip())
        for m in JSX_SINK.finditer(text):
            self._report(m.group(1), ("VUL-WEB-001", "CWE-79", "HTML sink"), raw, lineno + text.count("\n", 0, m.start()), "dangerouslySetInnerHTML")

    def _check_call(self, text: str, m, rule: tuple, raw: str, lineno: int):
        vul, cwe, kind, which = rule
        args = _args_of(text, m.end())
        if not args or (which == "shell" and not re.search(r"\bshell\s*:\s*true", " ".join(args))):
            return
        if which == "string" and re.match(r"^(?:\(|function\b|async\b|[\w$]+\s*=>)", args[0]):
            return
        expr = " , ".join(args) if which in ("any", "shell") else args[0]
        source, assembled = self.taint_of(expr)
        if source and (which != "assembled" or assembled):
            at = lineno + text.count("\n", 0, m.start())
            self.findings.append((vul, cwe, f"input reaches {kind}", rel(self.file), at, f"{text[m.start():m.end()]}...) <- {source}", ADVICE[cwe], _accepted(raw)))

    def _report(self, expr: str, rule: tuple, raw: str, lineno: int, what: str):
        vul, cwe, kind = rule
        source, _ = self.taint_of(expr)
        if source:
            self.findings.append((vul, cwe, f"input reaches {kind}", rel(self.file), lineno, f"{what} <- {source}", ADVICE[cwe], _accepted(raw)))

    def _calls(self, text: str):
        """A local function called with a tainted argument is walked once with that parameter tainted."""
        for name, (params, statements) in self.funcs.items():
            for m in re.finditer(rf"(?<![\w$.]){re.escape(name)}\(", text):
                passed = {p: f"argument of {name}: {self.taint_of(a)[0]}" for p, a in zip(params, _args_of(text, m.end())) if self.taint_of(a)[0]}
                if passed:
                    _Walk(self.file, self.lines, self.funcs, self.findings, follow=False).run(statements, passed)

    def _leave_scope(self, text: str):
        stripped = re.sub(r"`[^`]*`|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", "", text)
        self.depth += stripped.count("{") - stripped.count("}")
        self.tainted = {k: v for k, v in self.tainted.items() if v.depth <= self.depth}


def _accepted(raw: str):
    """The reason of an `aix: accepted VUL-…` marker anywhere in the statement, else None."""
    m = ACCEPT.search(raw)
    return (m.group(2).strip() or "accepted") if m else None


def _local_functions(text: str, lines: list) -> dict:
    """name -> (parameter names, statements of its body) for the named functions of a file."""
    funcs = {}
    for m in FUNC.finditer(text):
        name, params = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        start = text.count("\n", 0, m.start()) + 1
        body_start = text.find("{", m.end())
        depth, end = 0, body_start
        for end in range(body_start, len(text)):
            depth += (text[end] == "{") - (text[end] == "}")
            if depth == 0:
                break
        end_line = text.count("\n", 0, end) + 1
        names = [p.split("=")[0].split(":")[0].strip().lstrip(".") for p in params.split(",") if p.strip()]
        funcs[name] = (names, _statements(lines[start:end_line], start + 1)) if body_start >= 0 else (names, [])
    return funcs


def taint_file(file: Path, findings: list):
    text = file.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if any(SKIP_FILE.search(l) for l in lines[:MARKER_LINES]):
        return
    funcs = _local_functions(text, lines)
    _Walk(file, lines, funcs, findings).run(_statements(lines))


def taint(paths) -> list:
    """Findings for every JS/TS file under `paths`, deduplicated by (row, file, line)."""

    findings = []
    for p in paths:
        base = (ROOT / p) if not Path(p).is_absolute() else Path(p)
        for f in ([base] if base.is_file() else source_files([str(base)])):
            if f.suffix in JS_EXT:
                taint_file(f, findings)
    seen, out = set(), []
    for fx in findings:
        if (fx[0], fx[3], fx[4]) not in seen:
            seen.add((fx[0], fx[3], fx[4])); out.append(fx)
    return out
