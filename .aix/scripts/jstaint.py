"""Leaf: taint analysis of JavaScript/TypeScript files without a parser. Statement by statement (a statement may
span lines until its parentheses close), scoped by brace depth: input sources (Express/Koa/Fastify/Next request
objects, process.env/argv, location, URLSearchParams, formData) flow through assignments, destructuring, template
literals and concatenation; a sink reached without a sanitiser is a finding; local functions are followed one call
deep. Evidence to review, not proof: no types, no middleware, no cross-file."""
import re
from pathlib import Path

from codefiles import ROOT, rel, source_files
from securityrules import ACCEPT, ADVICE, SKIP_FILE, MARKER_LINES
from javatypes import RECEIVER_CALL, local_types

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
ASSIGN = re.compile(r"^\s*(?:export\s+)?((?:const|let|var)\s+)?(?:\{([^}]+)\}|([\w$]+))(?::\s*[^=]+?)?\s*=(?!=)\s*(.+?);?\s*$", re.S)
CONDITION = re.compile(r"^\s*(?:(?:else\s+)?if\s*\((?:[^()]|\([^()]*\))*\)\s*|else\s+)")
COLLECT = re.compile(r"^\s*([\w$]+)\.(?:add|addAll|put|putAll|set|append|push|unshift|offer|insert)\((.*)\)\s*;?\s*$", re.S)   # `list.add(param)`: the list is tainted
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


def strip_comments(text: str) -> str:
    """Comments out, strings kept whole: the `//` of `"http://x"` is not a comment."""
    return re.sub(STRINGS.pattern + "|" + COMMENTS.pattern, lambda m: " " if m.group(0).startswith(("//", "/*")) else m.group(0), text, flags=re.S)


def _code_only(expr: str) -> str:
    """The expression without the text of its string literals; a template literal keeps its `${...}` parts."""
    return STRINGS.sub(lambda m: " ".join(re.findall(r"\$\{([^}]*)\}", m.group(0))) if m.group(0).startswith("`") else '""', expr)


def _args_of(text: str, start: int) -> list:
    """The top-level arguments of the call whose `(` is at text[start - 1]; brackets and commas inside a string
    literal do not count (`"select id, name from t where x = " + x` is one argument)."""
    depth, args, cur, i = 0, [], "", start
    while i < len(text):
        ch = text[i]
        if ch in "\"'`":
            end = _string_end(text, i); cur += text[i:end]; i = end; continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            if depth == 0:
                break
            depth -= 1
        if ch == "," and depth == 0:
            args.append(cur); cur = ""
        else:
            cur += ch
        i += 1
    return [a.strip() for a in args + [cur] if a.strip()]


def _string_end(text: str, i: int) -> int:
    """The index just past the string literal opening at text[i]; an escaped quote stays inside."""
    quote, j = text[i], i + 1
    while j < len(text) and text[j] != quote:
        j += 2 if text[j] == "\\" else 1
    return min(j + 1, len(text))


def _names_of(destructured: str) -> list:
    """`{ a, b: c = 1 }` -> [a, c]."""
    names = []
    for part in destructured.split(","):
        part = part.split("=")[0]
        names.append((part.split(":")[-1] if ":" in part else part).strip())
    return [n for n in names if n]


class Rules:
    """What one language's taint walk looks for: JS/TS here (JS_RULES), Java in javataint.py. `head_sources(text)`
    names the parameters a statement declares as input (a `@RequestParam` in a Java method head); `assembled`
    says whether an expression builds a string."""
    def __init__(self, spec: dict):
        """spec: sources, sinks, assign_sinks, assign, loop, sanitised; optional jsx_sink, head_sources, assembled,
        parse_assign (an assign match -> (declared, names, expr)), aliases ([(regex on the assigned expression,
        sink rule, method names)]: a variable holding a response writer makes `w.println(x)` a sink)."""
        self.sources, self.sinks, self.assign_sinks = spec["sources"], spec["sinks"], spec["assign_sinks"]
        self.assign, self.loop, self.sanitised = spec["assign"], spec["loop"], spec["sanitised"]
        self.jsx_sink, self.head_sources = spec.get("jsx_sink"), spec.get("head_sources") or (lambda text: {})
        self.assembled = spec.get("assembled") or (lambda expr, clean: "${" in expr or "+" in clean)
        self.parse_assign = spec.get("parse_assign") or _parse_js_assign
        self.aliases = spec.get("aliases") or []


def _parse_js_assign(m) -> tuple:
    """(declared, names, expr) of a JS assignment match; a dotted target (`obj.x = ...`) is nobody's variable."""
    if m.group(3) and "." in m.group(3):
        return False, [], ""
    return bool(m.group(1)), (_names_of(m.group(2)) if m.group(2) else [m.group(3)]), m.group(4)


class _Taint:
    """A tainted variable: where the input came from, the brace depth it lives at, whether it was assembled (`+`, `${`)."""
    def __init__(self, source: str, depth: int, assembled: bool):
        self.source, self.depth, self.assembled = source, depth, assembled


class _Walk:
    """One pass over statements, with the tainted variables in scope, collecting sink hits."""
    def __init__(self, file: Path, lines: list, funcs: dict, findings: list, rules=None):
        self.file, self.lines, self.funcs, self.findings = file, lines, funcs, findings
        self.rules, self.follow = rules or JS_RULES, True   # follow: walk a function called with tainted arguments
        self.index = {}   # (name, arity) -> [(file, lines, params, statements)] in other files: the cross-file step by name (javataint)
        self.types, self.hops, self.stack = None, 2, []   # the Java type index, calls left to follow, the callees on the way (no cycles)
        self.walked = {}   # (file, first line, tainted parameters) -> hops it was walked with, shared: a callee is walked once per taint set and depth
        self.locals = {}   # name -> declared type, from the statements walked so far
        self.tainted, self.depth = {}, 0
        self.declared, self.alias = {}, {}   # name -> depth it was declared at; name -> sink rule it stands for (a writer)

    def run(self, statements: list, initial: dict = None):
        self.tainted = {k: _Taint(v, 0, False) for k, v in (initial or {}).items()}
        for lineno, raw in statements:
            text = strip_comments(raw)
            for name, source in self.rules.head_sources(text).items():   # parameters declared as input live in the body that opens here
                self.tainted[name] = _Taint(f"{name}: {source} (line {lineno})", self.depth + 1, False)
            self._assignments(text, lineno)
            self._sinks(text, raw, lineno)
            if self.types is not None:
                self.locals.update(local_types(text))
            if self.follow and self.hops > 0:
                self._calls(text)
            self._leave_scope(text)

    def taint_of(self, expr: str):
        """(source description, assembled) of an expression, or (None, False); sanitiser calls count as clean."""
        clean = self.rules.sanitised.sub("SAFE", _code_only(expr))
        m = self.rules.sources.search(clean)
        assembled = self.rules.assembled(expr, clean)
        if m:
            return m.group(0), assembled
        for name in IDENT.findall(clean):
            if name in self.tainted:
                return self.tainted[name].source, assembled or self.tainted[name].assembled
        return None, False

    def _assignments(self, text: str, lineno: int):
        m = self.rules.loop.search(text)
        if m:
            self._bind([m.group(1)], m.group(2), lineno, True); return
        conditional = CONDITION.match(text)
        if conditional:
            text = text[conditional.end():]   # `if (c) x = input;` / `else x = "";`: a branch adds taint, never clears it
        m = COLLECT.match(text)
        if m and self.taint_of(m.group(2))[0]:
            source, _ = self.taint_of(m.group(2))
            self.tainted[m.group(1)] = _Taint(f"{m.group(1)} holds {source} (line {lineno})", self.declared.get(m.group(1), self.depth), True)
            return
        m = self.rules.assign.match(text)
        if m:
            declared, names, expr = self.rules.parse_assign(m)
            self._bind(names, expr, lineno, declared, keep=bool(conditional))

    def _bind(self, names: list, expr: str, lineno: int, declared: bool, keep: bool = False):
        """Taint the names from the expression; a reassignment keeps the depth the variable was declared at, so
        `String p = ""; if (c) { p = request.getParameter(x); }` stays tainted after the block closes; `keep` (a
        conditional assignment) never clears what another branch may have tainted."""
        source, assembled = self.taint_of(expr)
        for name in names:
            if declared:
                self.declared[name] = self.depth
            depth = self.declared.get(name, self.depth)
            if source:
                self.tainted[name] = _Taint(f"{name} = ... from {source} (line {lineno})", depth, assembled)
            elif not keep:
                self.tainted.pop(name, None)
            for rx, rule, methods in self.rules.aliases:
                if rx.search(expr):
                    self.alias[name] = (rule, methods, depth)

    def _sinks(self, text: str, raw: str, lineno: int):
        for head, vul, cwe, kind, which in self.rules.sinks:
            for m in re.finditer(head, text):
                self._check_call(text, m, (vul, cwe, kind, which), raw, lineno)
        for rx, vul, cwe, kind in self.rules.assign_sinks:
            m = re.search(rx, text)
            if m:
                self._report(text[m.end():], (vul, cwe, kind), raw, lineno + text.count("\n", 0, m.start()), text[m.start():m.end()].strip())
        for m in (self.rules.jsx_sink.finditer(text) if self.rules.jsx_sink else []):
            self._report(m.group(1), ("VUL-WEB-001", "CWE-79", "HTML sink"), raw, lineno + text.count("\n", 0, m.start()), "dangerouslySetInnerHTML")
        for name, (rule, methods, _depth) in self.alias.items():
            for m in re.finditer(rf"\b{re.escape(name)}\.(?:{methods})\(", text):
                self._check_call(text, m, rule, raw, lineno)

    def _check_call(self, text: str, m, rule: tuple, raw: str, lineno: int):
        vul, cwe, kind, which = rule
        args = _args_of(text, m.end())
        if not args or (which == "shell" and not re.search(r"\bshell\s*:\s*true", " ".join(args))):
            return
        if which == "string" and re.match(r"^(?:\(|function\b|async\b|[\w$]+\s*=>)", args[0]):
            return
        expr = " , ".join(args) if which in ("any", "shell", "assembled") else args[0]   # an assembled string may be any argument (`search(base, filter)`); "first"/"first-assembled": the first only
        source, assembled = self.taint_of(expr)
        if source and (which not in ("assembled", "first-assembled") or assembled):
            at = lineno + text.count("\n", 0, m.start())
            self.findings.append((vul, cwe, f"input reaches {kind}", rel(self.file), at, f"{text[m.start():m.end()]}...) <- {source}", ADVICE[cwe], _accepted(raw)))

    def _report(self, expr: str, rule: tuple, raw: str, lineno: int, what: str):
        vul, cwe, kind = rule
        source, _ = self.taint_of(expr)
        if source:
            self.findings.append((vul, cwe, f"input reaches {kind}", rel(self.file), lineno, f"{what} <- {source}", ADVICE[cwe], _accepted(raw)))

    def _passed(self, name: str, params: list, text: str, end: int) -> dict:
        """The callee's parameters that receive a tainted argument, with where the taint came from."""
        return {p: f"argument of {name}: {self.taint_of(a)[0]}" for p, a in zip(params, _args_of(text, end)) if self.taint_of(a)[0]}

    def _walk_callee(self, file: Path, lines: list, statements: list, passed: dict):
        key = (file, statements[0][0] if statements else 0)
        memo = key + (tuple(sorted(passed)),)
        if key in self.stack or self.walked.get(memo, -1) >= self.hops - 1:
            return   # a cycle, or a callee this run has walked with the same tainted parameters as deep or deeper (the findings are already in)
        self.walked[memo] = self.hops - 1
        funcs = self.funcs if file == self.file else (self.types.methods.get(file, {}) if self.types else {})
        inner = _Walk(file, lines, funcs, self.findings, rules=self.rules)
        inner.index, inner.types, inner.hops, inner.stack, inner.walked = self.index, self.types, self.hops - 1, self.stack + [key], self.walked
        inner.follow = inner.hops > 0
        inner.run(statements, passed)

    def _calls(self, text: str):
        """A function called with a tainted argument is walked once with that parameter tainted: one of this file
        (self.funcs), one of another file through the receiver's declared type (self.types, Java), else by name
        and arity (self.index, Java); `hops` calls deep."""
        for name, (params, statements) in self.funcs.items():
            for m in re.finditer(rf"(?<![\w$.]){re.escape(name)}\(", text):
                passed = self._passed(name, params, text, m.end())
                if passed:
                    self._walk_callee(self.file, self.lines, statements, passed)
        self._named_calls(text, self._typed_calls(text) if self.types else set())

    def _named_calls(self, text: str, typed: set):
        """The cross-file step by name and arity, for the calls the type index did not resolve."""
        for m in re.finditer(r"(?<![\w$])([\w$]+)\(", text):
            if m.end() in typed:
                continue
            args = _args_of(text, m.end())
            for file, lines, params, statements in self.index.get((m.group(1), len(args)), [])[:3]:
                passed = self._passed(f"{m.group(1)} in {rel(file)}", params, text, m.end())
                if passed and file != self.file:
                    self._walk_callee(file, lines, statements, passed)

    def _typed_calls(self, text: str) -> set:
        """Calls followed through their receiver's type; returns the call positions resolved, which the name rule skips."""
        resolved = set()
        for m in RECEIVER_CALL.finditer(text):
            type_name = self.types.receiver_type(m, self.file, self.locals)
            if not type_name:
                continue
            args = _args_of(text, m.end())
            for file, params, statements in self.types.targets(type_name, m.group("method"), len(args)):
                resolved.add(m.end())
                passed = self._passed(f"{type_name}.{m.group('method')} in {rel(file)}", params, text, m.end())
                if passed:
                    self._walk_callee(file, self.types.lines[file], statements, passed)
        return resolved

    def _leave_scope(self, text: str):
        stripped = re.sub(r"`[^`]*`|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", "", text)
        self.depth += stripped.count("{") - stripped.count("}")
        self.tainted = {k: v for k, v in self.tainted.items() if v.depth <= self.depth}
        self.declared = {k: d for k, d in self.declared.items() if d <= self.depth}
        self.alias = {k: v for k, v in self.alias.items() if v[2] <= self.depth}


JS_RULES = Rules(dict(sources=SOURCES, sinks=SINKS, assign_sinks=ASSIGN_SINKS, assign=ASSIGN, loop=LOOP, sanitised=SANITISED, jsx_sink=JSX_SINK))


def _accepted(raw: str):
    """The reason of an `aix: accepted VUL-…` marker anywhere in the statement, else None."""
    m = ACCEPT.search(raw)
    return (m.group(2).strip() or "accepted") if m else None


def body_statements(text: str, lines: list, head_end: int, split=None) -> list:
    """The statements of the brace block that opens after `head_end`, with their line numbers; `split` turns lines
    into statements (the JS joiner by default, Java's in javataint)."""
    start = text.count("\n", 0, head_end) + 1
    body_start = text.find("{", head_end)
    if body_start < 0:
        return []
    depth, end = 0, body_start
    for end in range(body_start, len(text)):
        depth += (text[end] == "{") - (text[end] == "}")
        if depth == 0:
            break
    return (split or _statements)(lines[start:text.count("\n", 0, end) + 1], start + 1)


def _local_functions(text: str, lines: list) -> dict:
    """name -> (parameter names, statements of its body) for the named functions of a file."""
    funcs = {}
    for m in FUNC.finditer(text):
        name, params = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        names = [p.split("=")[0].split(":")[0].strip().lstrip(".") for p in params.split(",") if p.strip()]
        funcs[name] = (names, body_statements(text, lines, m.end()))
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
