"""Leaf: the "assembled, then used" rule of `aix code security`. A variable takes a string built from a literal plus a
value (`+`, f-string, .format, template literal, String.format, format!, %); within the next REACH lines it is the
argument of a dangerous call. What the literal looks like decides which sinks apply: an SQL keyword, a path, HTML,
a template, a URL; a shell or eval sink takes any literal. Shape only, no source: noisier than taint by design."""
import re

from codefiles import rel
from securityrules import ACCEPT

REACH = 40   # lines between the assembly and the use that are still one method
STRING = r"[fFrb]*(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`(?:[^`\\]|\\.)*`)"
ASSIGN = re.compile(r"^\s*(?:(?:const|let|var|val|final|String|var)\s+)?(\w+)(?:\s*:\s*[\w<>\[\]]+)?\s*=\s*(.+?)\s*;?\s*$")
ASSEMBLED = re.compile(r"\bf\"|\bf'|\.format\(|String\.format\(|\bformat!\(|\$\{|" + STRING + r"\s*(?:\+|%)|\+\s*" + STRING)
KIND_OF = (("sql", re.compile(r"^\s*(?:SELECT|INSERT|UPDATE|DELETE|WITH)\b", re.I)), ("html", re.compile(r"<\w")),
           ("template", re.compile(r"\{\{|\{%")), ("url", re.compile(r"^\s*https?://|^\s*//")), ("path", re.compile(r"[/\\]")))
PATH_BUILDERS = re.compile(r"os\.path\.join\(|path\.join\(|Paths\.get\(|Path::new\(|PathBuf::from\(")
SINKS = {  # kind -> (row, cwe, title, advice, {lang: sink regex; `name` is the variable})
    "shell": ("VUL-INJ-002", "CWE-78", "command assembled from strings, run with a shell below", "argument list without a shell; validate each argument",
              {"py": r"(?:os\.system|os\.popen)\([^;]*\b{name}\b|subprocess\.\w+\([^;]*\b{name}\b[^;]*shell\s*=\s*True",
               "js": r"\bexec(?:Sync)?\([^;]*\b{name}\b|\bspawn(?:Sync)?\([^;]*\b{name}\b[^;]*shell\s*:\s*true",
               "java": r"(?:Runtime\.getRuntime\(\)\.exec|new ProcessBuilder)\([^;]*\b{name}\b",
               "rust": r"Command::new\([^)]*\)[^;]*\"-c\"[^;]*\.arg\(\s*&?{name}\b"}),
    "eval": ("VUL-INJ-002", "CWE-95", "code assembled from strings, evaluated below", "never eval assembled code; a dispatch table",
             {"py": r"\b(?:eval|exec)\(\s*{name}\b", "js": r"(?:\beval|new Function)\(\s*{name}\b", "java": r"\.eval\(\s*{name}\b", "rust": r"$^"}),
    "path": ("VUL-INJ-002", "CWE-22", "path assembled from strings, opened below", "resolve against a base directory and reject anything outside it",
             {"py": r"(?:\bopen|send_file|os\.remove|os\.unlink|shutil\.\w+|Path)\(\s*{name}\b",
              "js": r"(?:\bfs(?:\.promises)?\.\w+|\b(?:readFile|writeFile|readdir|unlink|createReadStream|createWriteStream)(?:Sync)?|\.sendFile)\(\s*{name}\b",
              "java": r"(?:new File|Files\.\w+|Paths\.get|new FileInputStream|new FileOutputStream|new FileReader)\(\s*{name}\b",
              "rust": r"(?:File::open|File::create|fs::\w+|Path::new)\(\s*&?{name}\b"}),
    "html": ("VUL-WEB-001", "CWE-79", "HTML assembled from strings, sent below", "escape on output; never build HTML from values",
             {"py": r"(?:Markup|mark_safe|HttpResponse|render_template_string)\(\s*{name}\b",
              "js": r"\.innerHTML\s*=\s*{name}\b|(?:\.send|document\.write|\.insertAdjacentHTML)\([^;]*\b{name}\b",
              "java": r"getWriter\(\)\.(?:print|println|write)\(\s*{name}\b", "rust": r"Html\(\s*{name}\b"}),
    "template": ("VUL-INJ-002", "CWE-1336", "template assembled from strings, rendered below", "render a file template with a context",
                 {"py": r"(?:Template|render_template_string|from_string)\(\s*{name}\b", "js": r"\.compile\(\s*{name}\b", "java": r"$^", "rust": r"$^"}),
    "url": ("VUL-INPUT-001", "CWE-918", "URL assembled from strings, requested below", "allow-list hosts; block private ranges and redirects",
            {"py": r"(?:requests\.\w+|urlopen|httpx\.\w+)\(\s*{name}\b", "js": r"(?:\bfetch|axios(?:\.\w+)?|https?\.(?:get|request))\(\s*{name}\b",
             "java": r"(?:new URL|URI\.create|\.uri)\(\s*{name}\b", "rust": r"(?:reqwest::get|reqwest::blocking::get|Client::new\(\)\.get)\(\s*&?{name}\b"}),
    "sql": ("VUL-INJ-001", "CWE-89", "SQL built from strings, executed below", "PreparedStatement / parameters with ? placeholders; never concatenate values into the statement",
            {lang: r"(?:createQuery|createNativeQuery|executeQuery|executeUpdate|execute|prepareStatement|query|raw|exec)\(\s*{name}\b" for lang in ("py", "js", "java", "rust")}),
}


def kind_of(rhs: str) -> str:
    """What the assembled string is, by its literal text: sql, html, template, url, path, or 'any' (shell and eval only)."""
    literals = " ".join(m.strip("fFrb").strip("\"'`") for m in re.findall(STRING, rhs))
    for kind, rx in KIND_OF:
        if rx.search(literals) or (kind == "path" and PATH_BUILDERS.search(rhs)):
            return kind
    return "any"


def sinks_for(kind: str) -> list:
    """Shell and eval take any assembled string; the other sinks need a literal of their kind."""
    return ["shell", "eval"] + ([kind] if kind in SINKS else [])


def _use_lines(lines: list, i: int, name: str, rx, clean) -> list:
    """Every line after `i` where `rx` matches, until `name` is reassigned or the reach ends."""
    reassigned = re.compile(rf"^\s*(?:(?:const|let|var|val|final|String)\s+)?{re.escape(name)}\s*(?::\s*\w+)?\s*=(?!=)")
    out = []
    for j in range(i + 1, min(i + 1 + REACH, len(lines))):
        code = clean(lines[j])
        if rx.search(code):
            out.append(j)
        elif reassigned.match(code):
            break
    return out


def _finding(f, lines, i, j, rule) -> tuple:
    row, cwe, title, advice, _ = rule
    acc = ACCEPT.search(lines[j])
    accepted = f"{acc.group(1)} {acc.group(2).strip()}".strip() if acc and acc.group(1) == row else None
    return (row, cwe, title, rel(f), j + 1, f"{lines[i].strip()[:70]}  ...  {lines[j].strip()[:40]}", advice, accepted)


def findings(f, lines: list, lang: str, clean) -> list:
    """Every (assembled at line i, used at line j) pair of the file; `clean` strips the language's comments."""
    out = []
    for i, raw in enumerate(lines):
        m = ASSIGN.match(clean(raw))
        if not m or not (ASSEMBLED.search(m.group(2)) or PATH_BUILDERS.search(m.group(2))):
            continue
        for kind in sinks_for(kind_of(m.group(2))):
            rule = SINKS[kind]
            rx = re.compile(rule[4][lang].format(name=re.escape(m.group(1))))
            out += [_finding(f, lines, i, j, rule) for j in _use_lines(lines, i, m.group(1), rx, clean)]
    return out
