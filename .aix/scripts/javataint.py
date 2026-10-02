"""Leaf: taint analysis of Java files without a parser, the JS walk (jstaint._Walk) with Java rules. Statement by
statement, scoped by braces: request input (`@RequestParam`, `@PathVariable`, `@RequestBody` and the other Spring
binding annotations on a method's parameters; `request.getParameter(...)`, headers, cookies, the body of a servlet
request) flows through assignments, `+` concatenation and `String.format`; a sink reached without a sanitiser is a
finding; a method of the same file called with tainted arguments is followed one call deep. Evidence to review, not
proof: no types, no filters, no cross-file."""
import re
from pathlib import Path

from codefiles import ROOT, source_files
from jstaint import Rules, _Walk, body_statements, strip_comments
from securityrules import SKIP_FILE, MARKER_LINES

SOURCES = re.compile(r"\b(?:request|req|httpRequest|servletRequest)\.(?:getParameter(?:Values|Map|Names)?|getHeader(?:s|Names)?|getQueryString|getCookies|getInputStream|getReader|getRequestUR[IL]|getPathInfo|getPart)\("
                     r"|\bgetParameter\(|\bgetHeader\(")
BINDING = re.compile(r"@(?:RequestParam|PathVariable|RequestBody|RequestHeader|CookieValue|ModelAttribute|MatrixVariable|RequestPart|FormParam|QueryParam|PathParam|HeaderParam)\b")
SINKS = [  # (call head, VUL row, CWE, kind, which argument is dangerous)
    (r"\.(?:executeQuery|executeUpdate|execute|executeLargeUpdate|prepareStatement|prepareCall|createQuery|createNativeQuery|createSQLQuery|queryForList|queryForObject|queryForMap|update|batchUpdate)\(", "VUL-INJ-001", "CWE-89", "SQL statement", "assembled"),
    (r"\bRuntime\.getRuntime\(\)\.exec\(|\bnew\s+ProcessBuilder\(", "VUL-INJ-002", "CWE-78", "shell command", "any"),
    (r"\bnew\s+(?:File|FileInputStream|FileOutputStream|FileReader|FileWriter|RandomAccessFile)\(|\bPaths\.get\(|\bPath\.of\(|\bFiles\.(?:read\w*|write\w*|newInputStream|newOutputStream|delete\w*|copy|move|lines|exists)\(", "VUL-INJ-002", "CWE-22", "file path", "any"),   # `new File(dir, name)`: the name is the second argument
    (r"\.sendRedirect\(|\bnew\s+RedirectView\(", "VUL-WEB-003", "CWE-601", "redirect target", "first"),
    (r"\bnew\s+ObjectInputStream\(|\bXMLDecoder\(|\.readObject\(|\bXStream\(\)\.fromXML\(", "VUL-INPUT-002", "CWE-502", "deserialisation", "any"),
    (r"\bClass\.forName\(|\.loadClass\(", "VUL-INJ-002", "CWE-470", "class loading", "first"),
    (r"\bnew\s+URL\(|\.openConnection\(|\bHttpRequest\.newBuilder\(|\bRestTemplate\(\)\.\w+\(|\brestTemplate\.(?:getForObject|getForEntity|exchange|postForObject)\(", "VUL-INPUT-001", "CWE-918", "outbound request URL", "first"),   # a URI object alone requests nothing
    (r"\.getWriter\(\)\.(?:print|println|write|append)\(|\.getOutputStream\(\)\.(?:print|println|write)\(", "VUL-WEB-001", "CWE-79", "HTML response", "any"),
    (r"\.eval\(|\bScriptEngine\b[^;]*\.eval\(|\bnew\s+SpelExpressionParser\(\)\.parseExpression\(|\.parseExpression\(", "VUL-INJ-002", "CWE-95", "eval", "any"),
]
ASSIGN_SINKS = []
ASSIGN = re.compile(r"^\s*(?:final\s+)?(?:[\w.$]+(?:<[^=]*?>)?(?:\[\])*\s+)?([\w$]+)\s*(\+?=)(?!=)\s*(.+?);?\s*$", re.S)   # `String q = ...;`, `q = ...;`, `q += ...;`
LOOP = re.compile(r"\bfor\s*\(\s*(?:final\s+)?[\w.<>\[\]$]+\s+([\w$]+)\s*:\s*(.+?)\)")
SANITISED = re.compile(r"\b(?:Integer|Long|Short|Byte|Double|Float)\.(?:parseInt|parseLong|parseShort|parseByte|parseDouble|parseFloat|valueOf)\((?:[^()]|\([^()]*\))*\)"
                       r"|\bBoolean\.parseBoolean\((?:[^()]|\([^()]*\))*\)|\bUUID\.fromString\((?:[^()]|\([^()]*\))*\)"
                       r"|\b(?:URLEncoder|HtmlUtils|StringEscapeUtils|Encode|ESAPI\.encoder\(\)|Jsoup|FilenameUtils)\.\w+\((?:[^()]|\([^()]*\))*\)"
                       r"|\.(?:matches|normalize|getFileName)\((?:[^()]|\([^()]*\))*\)")
METHOD = re.compile(r"(?:^|\n)[ \t]*(?:@\w+(?:\([^)]*\))?[ \t]*)*(?:(?:public|private|protected|static|final|synchronized|abstract|default)\s+)*[\w.$<>\[\], ?]+?\s+([\w$]+)\s*\(((?:[^()]|\([^()]*\))*)\)\s*(?:throws\s+[\w.,\s]+)?\s*\{")   # a parameter may carry `@RequestParam("x")`
JAVA_EXT = (".java",)


def java_statements(lines: list, first: int = 1) -> list:
    """(line number, text) per statement: a Java statement runs until `;`, `{` or `}` closes it (an assignment
    continues on the next line after `=`), at most twelve lines; an annotation line stands alone."""
    out, i = [], 0
    while i < len(lines):
        text, j = lines[i], i
        while not strip_comments(text).rstrip().endswith((";", "{", "}")) and not text.strip().startswith(("@", "//", "*", "/*")) and text.strip() and j + 1 < len(lines) and j - i < 12:
            j += 1; text += "\n" + lines[j]
        out.append((first + i, text)); i = j + 1
    return out


def _param_names(params: str) -> list:
    """`@RequestParam("id") String account, Map<String, String> m` -> [account, m]: commas inside generics or
    annotation arguments do not split."""
    names, depth, chunk = [], 0, ""
    for ch in params + ",":
        if ch == "," and depth == 0:
            words = re.findall(r"[\w$]+", chunk.rsplit(")", 1)[-1] if "@" in chunk else chunk)
            if words:
                names.append(words[-1])
            chunk = ""
        else:
            depth += ch in "<(["; depth -= ch in ">)]"; chunk += ch
    return names


def _assembled(expr: str, clean: str) -> bool:
    return "+" in clean or bool(re.search(r"\b(?:String\.format|\.concat|\.format|\.replace|StringBuilder|\.append)\b", clean))


def head_sources(text: str) -> dict:
    """{parameter: description} for a method head whose parameters carry a binding annotation."""
    m = METHOD.search(text)
    if not m or not BINDING.search(m.group(2)):
        return {}
    out = {}
    for chunk in re.split(r",(?![^<(]*[>)])", m.group(2)):
        b = BINDING.search(chunk)
        words = re.findall(r"[\w$]+", chunk.rsplit(")", 1)[-1] if "@" in chunk and ")" in chunk else chunk)
        if b and words:
            out[words[-1]] = b.group(0)
    return out


JAVA_RULES = Rules(dict(sources=SOURCES, sinks=SINKS, assign_sinks=ASSIGN_SINKS, assign=ASSIGN, loop=LOOP, sanitised=SANITISED, head_sources=head_sources, assembled=_assembled))


def _methods(text: str, lines: list) -> dict:
    """name -> (parameter names, statements of the body) for the methods of a file; a called method is walked once
    with the tainted arguments bound to its parameters."""
    return {m.group(1): (_param_names(m.group(2)), body_statements(text, lines, m.end() - 1, java_statements)) for m in METHOD.finditer(text)
            if m.group(1) not in ("if", "for", "while", "switch", "catch", "synchronized", "return", "new")}


def _load(file: Path):
    """(text, lines) of a Java file, or None when a marker skips it."""
    text = file.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    return None if any(SKIP_FILE.search(l) for l in lines[:MARKER_LINES]) else (text, lines)


def method_index(files: dict) -> dict:
    """(name, arity) -> [(file, lines, params, statements)] over every file: how a call reaches a method of another
    file (a controller's parameter into a service's SQL). By name and arity, no types: a false join still needs a
    sink in the callee to show."""
    index = {}
    for file, (text, lines) in files.items():
        for name, (params, statements) in _methods(text, lines).items():
            index.setdefault((name, len(params)), []).append((file, lines, params, statements))
    return index


def taint_file(file: Path, findings: list, index: dict = None):
    loaded = _load(file)
    if loaded is None:
        return
    text, lines = loaded
    walk = _Walk(file, lines, _methods(text, lines), findings, rules=JAVA_RULES)
    walk.index = index or {}
    walk.run(java_statements(lines))


def taint(paths) -> list:
    """Findings for every Java file under `paths`, deduplicated by (row, file, line); calls into other files of the
    same paths are followed one level deep."""
    files = {}
    for p in paths:
        base = (ROOT / p) if not Path(p).is_absolute() else Path(p)
        for f in ([base] if base.is_file() else source_files([str(base)])):
            if f.suffix in JAVA_EXT and _load(f) is not None:
                files[f] = _load(f)
    index = method_index(files)
    findings = []
    for f in files:
        taint_file(f, findings, index)
    seen, out = set(), []
    for fx in findings:
        if (fx[0], fx[3], fx[4]) not in seen:
            seen.add((fx[0], fx[3], fx[4])); out.append(fx)
    return out
