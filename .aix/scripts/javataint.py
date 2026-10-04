"""Leaf: taint analysis of Java files without a parser, the JS walk (jstaint._Walk) with Java rules. Statement by
statement, scoped by braces: request input (`@RequestParam`, `@PathVariable`, `@RequestBody` and the other Spring
binding annotations on a method's parameters; `request.getParameter(...)`, headers, cookies, the body of a servlet
request) flows through assignments, `+` concatenation and `String.format`; a sink reached without a sanitiser is a
finding; a method called with tainted arguments is followed two calls deep, in this file or in the class the receiver's
declared type names (javatypes), else by name and arity. Evidence to review, not
proof: no types, no filters, no cross-file."""
import re
from pathlib import Path

from codefiles import ROOT, source_files
from javatypes import TypeIndex
from jstaint import Rules, _Walk, body_statements, strip_comments
from securityrules import SKIP_FILE, MARKER_LINES

SOURCES = re.compile(r"\b(?:request|req|httpRequest|servletRequest)\.(?:getParameter(?:Values|Map|Names)?|getHeader(?:s|Names)?|getQueryString|getCookies|getInputStream|getReader|getRequestUR[IL]|getPathInfo|getPart)\("
                     r"|\bgetParameter\(|\bgetHeader\(")
BINDING = re.compile(r"@(?:RequestParam|PathVariable|RequestBody|RequestHeader|CookieValue|ModelAttribute|MatrixVariable|RequestPart|FormParam|QueryParam|PathParam|HeaderParam)\b")
Q = r"(?:[\w$]+\.)*"   # a fully qualified name: `new java.io.File(`, `javax.crypto.Cipher.getInstance(`
SINKS = [  # (call head, VUL row, CWE, kind, which argument is dangerous)
    # SQL: the statement is the first argument. A method that takes only a statement is a sink for a tainted first argument, raw or
    # assembled; a method that also takes bound parameters (`update(sql, params)`) only for an assembled one: a tainted value among the
    # parameters never touches the statement (CodeQL benchmark, section 18). `.execute(` is JDBC only on a statement-like receiver.
    (r"\.(?:executeQuery|executeUpdate|executeLargeUpdate|prepareStatement|prepareCall|createQuery|createNativeQuery|createSQLQuery|nativeQuery|addBatch)\(", "VUL-INJ-001", "CWE-89", "SQL statement", "first"),
    (r"\b(?:[\w$]*(?:[sS]tatement|[sS]tmt|[jJ]dbc|[tT]emplate|[sS]ession|[qQ]uery|[sS]ql)[\w$]*|ps|st|cs|em)\.execute\(", "VUL-INJ-001", "CWE-89", "SQL statement", "first"),
    (r"\.(?:queryForList|queryForObject|queryForMap|update|batchUpdate|query)\(", "VUL-INJ-001", "CWE-89", "SQL statement", "first-assembled"),
    (rf"\b{Q}Runtime\.getRuntime\(\)\.exec\(|\b[\w$]+\.exec\(|\bnew\s+{Q}ProcessBuilder\(|\.command\(", "VUL-INJ-002", "CWE-78", "shell command", "any"),
    (rf"\bnew\s+{Q}(?:File|FileInputStream|FileOutputStream|FileReader|FileWriter|RandomAccessFile|PrintWriter|FileSystemResource)\(|\b{Q}Paths\.get\(|\b{Q}Path\.of\(|\b{Q}Files\.(?:read\w*|write\w*|newInputStream|newOutputStream|newBufferedReader|newBufferedWriter|delete\w*|copy|move|lines|exists|createFile|createDirectory)\(", "VUL-INJ-002", "CWE-22", "file path", "any"),   # `new File(dir, name)`: the name is the second argument
    (r"\.sendRedirect\(|\bnew\s+(?:[\w$]+\.)*RedirectView\(", "VUL-WEB-003", "CWE-601", "redirect target", "first"),
    (rf"\bnew\s+{Q}ObjectInputStream\(|\bnew\s+{Q}XMLDecoder\(|\.readObject\(|\.fromXML\(", "VUL-INPUT-002", "CWE-502", "deserialisation", "any"),
    (r"\b(?![\w$]*[jJ][sS][oO][nN])(?:[\w$]*(?:[bB]uilder|[pP]arser|[fF]actory|[uU]nmarshaller|[dD]om|[xX]ml|[sS]ax|[sS]tax|[rR]eader)[\w$]*|db|dbf|xif|xef)\.(?:parse|createXMLStreamReader|createXMLEventReader|unmarshal)\(", "VUL-INPUT-001", "CWE-611", "XML document parsed", "any"),   # XXE: a tainted document into a parser
    (rf"\b{Q}Class\.forName\(|\.loadClass\(", "VUL-INJ-002", "CWE-470", "class loading", "first"),
    (rf"\bnew\s+{Q}URL\(|\.openConnection\(|\b{Q}HttpRequest\.newBuilder\(|\bRestTemplate\(\)\.\w+\(|\brestTemplate\.(?:getForObject|getForEntity|exchange|postForObject)\(", "VUL-INPUT-001", "CWE-918", "outbound request URL", "first"),   # a URI object alone requests nothing
    (r"\.getWriter\(\)\.(?:print|println|printf|format|write|append)\(|\.getOutputStream\(\)\.(?:print|println|write)\(", "VUL-WEB-001", "CWE-79", "HTML response", "any"),
    (rf"\.eval\(|\bScriptEngine\b[^;]*\.eval\(|\bnew\s+{Q}SpelExpressionParser\(\)\.parseExpression\(|\.parseExpression\(", "VUL-INJ-002", "CWE-95", "eval", "any"),
    (r"(?:\.getSession\(\)|\bsession)\.setAttribute\(", "VUL-INPUT-001", "CWE-501", "session attribute", "any"),   # trust boundary: input stored as if trusted
    (r"\.search\(", "VUL-INJ-001", "CWE-90", "LDAP query", "assembled"),
    (r"\b\w*[xX][pP]ath\w*\.(?:evaluate|compile)\(|\bxp\.(?:evaluate|compile)\(", "VUL-INJ-001", "CWE-643", "XPath query", "assembled"),
]
WRITER = re.compile(r"\.getWriter\(\)|\.getOutputStream\(\)|\bnew\s+(?:[\w$]+\.)*PrintWriter\(\s*response")   # a variable holding the response writer
SESSION = re.compile(r"\.getSession\(")   # a variable holding the session
ASSIGN_SINKS = []
ASSIGN = re.compile(r"^\s*(?:final\s+)?((?:[\w.$]+(?:<[^=]*?>)?(?:\[\])*\s+))?([\w$]+)\s*(\+?=)(?!=)\s*(.+?);?\s*$", re.S)   # `String q = ...;`, `q = ...;`, `q += ...;`


def parse_assign(m) -> tuple:
    """(declared, names, expr): `String q = x` declares; `q += x` is `q + (x)`, assembled and never a declaration."""
    name, op, expr = m.group(2), m.group(3), m.group(4)
    return bool(m.group(1)), [name], (f"{name} + ({expr})" if op == "+=" else expr)
LOOP = re.compile(r"\bfor\s*\(\s*(?:final\s+)?[\w.<>\[\]$]+\s+([\w$]+)\s*:\s*(.+?)\)")
SANITISED = re.compile(r"\b(?:Integer|Long|Short|Byte|Double|Float)\.(?:parseInt|parseLong|parseShort|parseByte|parseDouble|parseFloat|valueOf)\((?:[^()]|\([^()]*\))*\)"
                       r"|\bBoolean\.parseBoolean\((?:[^()]|\([^()]*\))*\)|\bUUID\.fromString\((?:[^()]|\([^()]*\))*\)"
                       r"|\b(?:URLEncoder|HtmlUtils|StringEscapeUtils|Encode|ESAPI\.encoder\(\)|Jsoup|FilenameUtils)\.\w+\((?:[^()]|\([^()]*\))*\)"
                       r"|\.(?:matches|normalize|getFileName)\((?:[^()]|\([^()]*\))*\)")
METHOD = re.compile(r"(?:^|\n)[ \t]*(?:@\w+(?:\([^)]*\))?[ \t]*)*(?:(?:public|private|protected|static|final|synchronized|abstract|default)\s+)*(?:@[\w.$]+(?:\([^)]*\))?\s+)*[\w.$<>\[\], ?]+?\s+([\w$]+)\s*\(((?:[^()]|\([^()]*\))*)\)\s*(?:throws\s+[\w.,\s]+)?\s*\{")   # a parameter may carry `@RequestParam("x")`; `public @ResponseBody T m(` is a method
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


JAVA_RULES = Rules(dict(sources=SOURCES, sinks=SINKS, assign_sinks=ASSIGN_SINKS, assign=ASSIGN, loop=LOOP, sanitised=SANITISED, head_sources=head_sources,
                        assembled=_assembled, parse_assign=parse_assign,
                        aliases=[(WRITER, ("VUL-WEB-001", "CWE-79", "HTML response", "any"), "print|println|printf|format|write|append"),
                                 (SESSION, ("VUL-INPUT-001", "CWE-501", "session attribute", "any"), "setAttribute|putValue")]))


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


def taint_file(file: Path, findings: list, index: dict = None, types: TypeIndex = None, walked: dict = None):
    loaded = _load(file)
    if loaded is None:
        return
    text, lines = loaded
    walk = _Walk(file, lines, _methods(text, lines), findings, rules=JAVA_RULES)
    walk.index, walk.types, walk.walked = index or {}, types, walked if walked is not None else {}
    walk.run(java_statements(lines))


def type_index(files: dict) -> TypeIndex:
    """The project's classes, parents, fields and methods, built once per run (javatypes)."""
    types = TypeIndex()
    for file, (text, lines) in files.items():
        types.add_file(file, text, lines, _methods(text, lines))
    return types


def taint(paths) -> list:
    """Findings for every Java file under `paths`, deduplicated by (row, file, line); calls into other files of the
    same paths are followed two levels deep, through the receiver's declared type when it can be read."""
    files = {}
    for p in paths:
        base = (ROOT / p) if not Path(p).is_absolute() else Path(p)
        for f in ([base] if base.is_file() else source_files([str(base)])):
            if f.suffix in JAVA_EXT and _load(f) is not None:
                files[f] = _load(f)
    index, types, walked = method_index(files), type_index(files), {}
    findings = []
    for f in files:
        taint_file(f, findings, index, types, walked)
    seen, out = set(), []
    for fx in findings:
        if (fx[0], fx[3], fx[4]) not in seen:
            seen.add((fx[0], fx[3], fx[4])); out.append(fx)
    return out
