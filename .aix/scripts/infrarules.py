"""Leaf: security rules over infrastructure and framework configuration files, the categories a semgrep run adds to
the per-line rules (docs/tests/benchmark-engines.md, table 3): GitHub Actions, dependabot, .npmrc, Dockerfiles,
Kubernetes manifests, docker-compose, express session cookies, script tags without integrity, Spring actuator and
request mappings, postMessage to any origin. Each check reads one file and yields register-shaped findings
(vul, cwe, title, file, line, snippet, advice, accepted=None) at the line the rule anchors on."""
import re
from pathlib import Path

from codefiles import ROOT, SKIP, rel
from depscan import scan_dockerfile

SHA = re.compile(r"@[0-9a-f]{40}\b")
USES = re.compile(r"^\s*-?\s*uses:\s*([\w.-]+/[\w./-]+)@(\S+)")
DANGEROUS_CONTEXT = re.compile(   # the contexts an outsider writes (titles, bodies, branch names, commit messages), semgrep's list
    r"\$\{\{\s*(?:github\.(?:head_ref|ref_name|base_ref"
    r"|event\.(?:issue|pull_request|comment|review|review_comment|discussion|discussion_comment)\.(?:title|body|head\.(?:ref|label|repo\.\w+)|user\.\w+)"
    r"|event\.(?:commits\[[^\]]*\]|head_commit)\.(?:message|author\.\w+|committer\.\w+)"
    r"|event\.workflow_run\.(?:head_branch|head_commit\.(?:message|author\.\w+)|head_repository\.\w+)"
    r"|event\.pages\[[^\]]*\]\.page_name|event\.inputs\.[\w.]+|event\.client_payload\.[\w.]+))\b")
# not listed: `steps.*.outputs` and `needs.*.outputs` (set by the workflow's own steps) and `inputs.*` of a reusable workflow
CURL_PIPE = re.compile(r"\b(?:curl|wget)\b[^|\n]*\|\s*(?:sudo\s+)?(?:ba|z)?sh\b")
K8S_KIND = re.compile(r"^kind:\s*(Deployment|Pod|StatefulSet|DaemonSet|Job|CronJob|ReplicaSet)\b", re.M)
EXTERNAL_ASSET = re.compile(r"<(?:script[^>]*?\ssrc|link[^>]*?\shref)\s*=\s*[\"'](?:https?:)?//[^\"']+[\"'][^>]*?>", re.I | re.S)   # a tag may span lines
REQUEST_MAPPING = re.compile(r"@RequestMapping\s*\(")
POST_MESSAGE = re.compile(r"\.postMessage\s*\(")
SESSION_CALL = re.compile(r"\b(?:session|cookieSession)\s*\(\s*\{")
COOKIE_OPTIONS = ("httpOnly", "secure", "domain", "path")


def _lines(f: Path) -> list:
    return f.read_text(encoding="utf-8", errors="replace").splitlines()


SNIPPET = 110


def _finding(rule: tuple, f: Path, i: int, snippet: str):
    """A register-shaped finding: rule = (vul, cwe, title, advice)."""
    vul, cwe, title, advice = rule
    return (vul, cwe, title, rel(f), i, snippet.strip()[:SNIPPET], advice, None)


def _block_end(lines: list, start: int) -> int:
    """The last index of the YAML block starting at `start` (its indented continuation)."""
    indent = len(lines[start]) - len(lines[start].lstrip())
    end = start
    for j in range(start + 1, len(lines)):
        s = lines[j]
        if s.strip() and not s.lstrip().startswith("#") and len(s) - len(s.lstrip()) <= indent:
            break
        end = j
    return end


def _call_text(lines: list, i: int) -> str:
    """The call starting on line i up to the parenthesis that closes it (a few lines at most)."""
    text, depth, started = "", 0, False
    for raw in lines[i:i + 40]:
        text += raw + "\n"
        depth += raw.count("(") - raw.count(")"); started |= "(" in raw
        if started and depth <= 0:
            break
    return text


# ---- GitHub Actions, dependabot, .npmrc ----------------------------------------------------------------------------

def workflow(f: Path) -> list:
    out, lines = [], _lines(f)
    for i, raw in enumerate(lines, 1):
        m = USES.match(raw)
        if m and not SHA.search(raw) and not m.group(1).startswith("./"):
            out.append(_finding(("VUL-DEP-001", "CWE-829", "action pinned to a mutable tag", f"pin {m.group(1)} to a commit SHA (`@<40-hex> # {m.group(2)}`): a tag can be moved to other code"), f, i, raw))
        if re.match(r"^\s*run:", raw):
            block = "\n".join(lines[i - 1:_block_end(lines, i - 1) + 1])
            if DANGEROUS_CONTEXT.search(block):
                out.append(_finding(("VUL-INJ-002", "CWE-78", "workflow shell injection: untrusted context in run", "pass the value through `env:` and quote \"$VAR\" in the script; an expression is pasted into the shell as text"), f, i, DANGEROUS_CONTEXT.search(block).group(0)))
            if CURL_PIPE.search(block):
                out.append(_finding(("VUL-DEP-001", "CWE-494", "remote script piped to a shell", "download, verify (checksum or signature), then run"), f, i, CURL_PIPE.search(block).group(0)))
    return out


def dependabot(f: Path) -> list:
    out, lines = [], _lines(f)
    for i, raw in enumerate(lines, 1):
        if re.match(r"^\s*-\s*package-ecosystem:", raw):
            block = "\n".join(lines[i - 1:_block_end(lines, i - 1) + 1])
            if not re.search(r"^\s+cooldown:", block, re.M):
                out.append(_finding(("VUL-DEP-001", "CWE-1104", "dependabot update without a cooldown", "add `cooldown:` (days) so a freshly published, possibly hijacked, version is not taken the hour it appears"), f, i, raw))
    return out


def npmrc(f: Path) -> list:
    text = f.read_text(encoding="utf-8", errors="replace")
    if "min-release-age" in text or "minimum-release-age" in text:
        return []
    return [_finding(("VUL-DEP-001", "CWE-1104", ".npmrc without a minimum release age", "add `min-release-age=7` (days): a freshly published version is the one most likely to be hijacked"), f, 1, (text.splitlines() or [""])[0])]


# ---- containers -----------------------------------------------------------------------------------------------------

def dockerfile(f: Path) -> list:
    return [_finding(("VUL-INFRA-001", "CWE-250", "sudo in a Dockerfile", "run the step as root at build time and switch to USER afterwards; sudo in an image is an escalation path"), f, i, raw)
            for i, raw in enumerate(_lines(f), 1) if re.match(r"^\s*RUN\b.*\bsudo\b", raw)]


ROOT_RULE = ("VUL-INFRA-001", "CWE-250", "container may run as root", "securityContext: runAsNonRoot: true (and a numeric runAsUser)")
ESCALATION_RULE = ("VUL-INFRA-001", "CWE-250", "container allows privilege escalation", "securityContext: allowPrivilegeEscalation: false")


def _container_findings(f: Path, lines: list, j: int, pod: str) -> list:
    """The two checks on the container item starting at index j; `pod` is the surrounding pod spec."""
    item = "\n".join(lines[j:_block_end(lines, j) + 1])
    out = []
    if not re.search(r"runAsNonRoot:\s*true", item + pod):
        out.append(_finding(ROOT_RULE, f, j + 1, lines[j]))
    if not re.search(r"allowPrivilegeEscalation:\s*false", item):
        out.append(_finding(ESCALATION_RULE, f, j + 1, lines[j]))
    return out


def kubernetes(f: Path) -> list:
    """Every container of a workload without runAsNonRoot: true or allowPrivilegeEscalation: false in reach."""
    text = f.read_text(encoding="utf-8", errors="replace")
    if not K8S_KIND.search(text):
        return []
    out, lines = [], text.splitlines()
    for i, raw in enumerate(lines, 1):
        if not re.match(r"^\s*containers:\s*$", raw):
            continue
        pod = "\n".join(lines[max(0, i - 40):i - 1])   # the pod spec above (a pod-level securityContext covers every container)
        out += [fx for j in _container_items(lines, i, _block_end(lines, i - 1)) for fx in _container_findings(f, lines, j, pod)]
    return out


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _container_items(lines: list, start: int, end: int) -> list:
    """Indexes of the list items directly under `containers:` (an `- name:` of an env entry sits deeper)."""
    first = next((j for j in range(start, end + 1) if re.match(r"^\s*-\s", lines[j])), None)
    if first is None:
        return []
    return [j for j in range(start, end + 1) if re.match(r"^\s*-\s*(?:name|image):", lines[j]) and _indent(lines[j]) == _indent(lines[first])]


NO_NEW_PRIV = ("VUL-INFRA-001", "CWE-250", "compose service without no-new-privileges", "security_opt: [no-new-privileges:true]")
WRITABLE_FS = ("VUL-INFRA-001", "CWE-732", "compose service with a writable root filesystem", "read_only: true, with tmpfs or volumes for what must be written")


def _service_findings(f: Path, lines: list, i: int) -> list:
    """The two checks on the service whose key is on line i (1-based); a service without `image:` is built here, skipped."""
    block = "\n".join(lines[i - 1:_block_end(lines, i - 1) + 1])
    if not re.search(r"^\s+image:", block, re.M):
        return []
    out = [] if "no-new-privileges" in block else [_finding(NO_NEW_PRIV, f, i, lines[i - 1])]
    return out + ([] if re.search(r"read_only:\s*true", block) else [_finding(WRITABLE_FS, f, i, lines[i - 1])])


def _service_lines(lines: list) -> list:
    """1-based lines of the service keys under `services:`."""
    out, in_services = [], False
    for i, raw in enumerate(lines, 1):
        if re.match(r"^services:\s*$", raw):
            in_services = True
        elif re.match(r"^\S", raw):
            in_services = False
        elif in_services and re.match(r"^  [\w.-]+:\s*$", raw):
            out.append(i)
    return out


def compose(f: Path) -> list:
    """Every service with an image: no-new-privileges and a read-only root filesystem, or a finding each."""
    lines = _lines(f)
    return [fx for i in _service_lines(lines) for fx in _service_findings(f, lines, i)]


# ---- frameworks and pages -------------------------------------------------------------------------------------------

def express_sessions(f: Path) -> list:
    out, lines = [], _lines(f)
    for i, raw in enumerate(lines, 1):
        if not SESSION_CALL.search(raw):
            continue
        text = _call_text(lines, i - 1)
        missing = [k for k in COOKIE_OPTIONS if not re.search(rf"\b{k}\s*:", text)] + (["expires or maxAge"] if not re.search(r"\b(?:expires|maxAge)\s*:", text) else []) + (["name"] if not re.search(r"\b(?:name|key)\s*:", text) else [])
        if missing:
            out.append(_finding(("VUL-AUTHN-002", "CWE-614", "session cookie without " + ", ".join(missing), "set cookie: { httpOnly: true, secure: true, domain, path, maxAge } and a non-default name"), f, i, raw))
        m = re.search(r"\bsecret\s*:\s*['\"`][^'\"`]+['\"`]", text)
        if m:
            out.append(_finding(("VUL-SECRET-001", "CWE-798", "session secret hard-coded", "read the secret from the environment or a secret manager"), f, i - 1 + text[:m.start()].count("\n") + 1, m.group(0)))
    return out


SRI_RULE = ("VUL-DEP-001", "CWE-353", "external script or stylesheet without integrity", "add integrity=\"sha384-...\" crossorigin=\"anonymous\" (subresource integrity), or serve the file yourself")


def page_assets(f: Path) -> list:
    text = f.read_text(encoding="utf-8", errors="replace")
    return [_finding(SRI_RULE, f, text.count("\n", 0, m.start()) + 1, " ".join(m.group(0).split()))
            for m in EXTERNAL_ASSET.finditer(text) if "integrity=" not in m.group(0).lower()]


ACTUATOR_RULE = ("VUL-SECRET-002", "CWE-16", "every actuator endpoint exposed", "include only health,info; env, heapdump and beans leak configuration and memory")


def _annotates_a_class(lines: list, i: int) -> bool:
    """The declaration after the annotation on line i (0-based), past any further annotations (multi-line ones
    included), is a class, interface, enum or record."""
    depth = lines[i].count("(") - lines[i].count(")")
    for raw in lines[i + 1:i + 30]:
        text = raw.strip()
        inside = depth > 0 or text.startswith("@") or text.startswith((")", "}"))
        depth += raw.count("(") - raw.count(")")
        if text and not inside:
            return bool(re.search(r"\b(?:class|interface|enum|record)\b", raw))
    return False


XML_FACTORY = re.compile(r"\b(DocumentBuilderFactory|SAXParserFactory|XMLInputFactory|TransformerFactory|SchemaFactory|XMLReaderFactory|SAXReader|SAXBuilder|XMLReader)\b[^;]*\b(?:newInstance|newDefaultInstance|createXMLReader|newFactory)\s*\(|\bnew\s+(?:SAXReader|SAXBuilder)\s*\(")
XML_HARDENED = re.compile(r"disallow-doctype-decl|ACCESS_EXTERNAL_DTD|ACCESS_EXTERNAL_SCHEMA|FEATURE_SECURE_PROCESSING|external-general-entities|external-parameter-entities|SUPPORT_DTD|IS_SUPPORTING_EXTERNAL_ENTITIES|setExpandEntityReferences\(\s*false|setXIncludeAware\(\s*false")
XXE_RULE = ("VUL-INPUT-001", "CWE-611", "XML parser without external entities disabled (XXE)", "set disallow-doctype-decl true (or ACCESS_EXTERNAL_DTD/SCHEMA to \"\") on the factory before parsing")
BASIC_RULE = ("VUL-SECRET-002", "CWE-319", "HTTP Basic authentication without requiresSecure()", "requiresChannel().anyRequest().requiresSecure(), or TLS at the edge with the reason beside it")
PERMIT_RULE = ("VUL-WEB-002", "CWE-285", "every request permitted (anyRequest().permitAll())", "authenticated() by default; permitAll() on the public paths only")


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _method_bodies(lines: list) -> list:
    """(start index, end index) of each brace block that opens on a Java method head, for checks scoped to a method."""
    out, text = [], "\n".join(lines)
    for m in re.finditer(r"\)\s*(?:throws\s+[\w.,\s]+?)?\s*\{", text):
        start = text.count("\n", 0, m.end())
        out.append((start, _block_end(lines, start)))
    return out


def _method_scope(lines: list, i: int) -> tuple:
    """The method body (start, end) around line index i, or a 30-line window when no method head encloses it."""
    return next(((a, b) for a, b in _method_bodies(lines) if a <= i <= b), (max(0, i - 30), min(len(lines) - 1, i + 30)))


def _unless_in_scope(rule: tuple, trigger, guard, f: Path, lines: list) -> list:
    """A line matching `trigger` whose enclosing method never matches `guard`: the trigger's line is the finding."""
    out = []
    for i, raw in enumerate(lines):
        if trigger.search(raw):
            a, b = _method_scope(lines, i)
            if not guard.search("\n".join(lines[a:b + 1])):
                out.append(_finding(rule, f, i + 1, raw))
    return out


def _xxe(f: Path, lines: list) -> list:
    """An XML parser factory created in a method that never hardens one."""
    return _unless_in_scope(XXE_RULE, XML_FACTORY, XML_HARDENED, f, lines)


def _security_config(f: Path, lines: list) -> list:
    """Spring Security configuration: Basic auth in a filter chain that never enforces TLS, everything permitted."""
    out = _unless_in_scope(BASIC_RULE, re.compile(r"\.httpBasic\("), re.compile(r"requiresSecure\(\)"), f, lines)
    text = "\n".join(lines)
    for m in re.finditer(r"\.anyRequest\(\)\s*\.permitAll\(\)", text):
        out.append(_finding(PERMIT_RULE, f, _line_of(text, m.start()), m.group(0)))
    return out


def spring(f: Path) -> list:
    out, lines = [], _lines(f)
    if f.suffix == ".java":
        out += _xxe(f, lines) + _security_config(f, lines)
    for i, raw in enumerate(lines, 1):
        if f.suffix == ".java" and REQUEST_MAPPING.search(raw) and not re.search(r"\bmethod\s*=", _call_text(lines, i - 1)) and not _annotates_a_class(lines, i - 1):
            out.append(_finding(("VUL-WEB-002", "CWE-352", "@RequestMapping without a method: every verb, CSRF-exposed", "@GetMapping / @PostMapping, or method = RequestMethod.GET"), f, i, raw))
        if f.suffix != ".java" and re.match(r"^\s*management\.endpoints\.web\.exposure\.include\s*[=:]\s*\*", raw):
            out.append(_finding(("VUL-SECRET-002", "CWE-16", "every actuator endpoint exposed", "include only health,info; env, heapdump and beans leak configuration and memory"), f, i, raw))
    return out


def spring_yaml(f: Path) -> list:
    text = f.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"exposure:\s*\n\s+include:\s*['\"]?\*['\"]?", text)
    return [_finding(ACTUATOR_RULE, f, text.count("\n", 0, m.start()) + 2, m.group(0).splitlines()[-1])] if m else []


def post_message(f: Path) -> list:
    out, lines = [], _lines(f)
    for i, raw in enumerate(lines, 1):
        if POST_MESSAGE.search(raw) and re.search(r"""['"`]\*['"`]""", _call_text(lines, i - 1)):
            out.append(_finding(("VUL-WEB-001", "CWE-345", "postMessage to any origin", "name the target origin; '*' lets any embedding page read the message"), f, i, raw))
    return out


# ---- routing by file --------------------------------------------------------------------------------------------------

YAML = (".yml", ".yaml")
ROUTES = [  # (applies to this file?, checks)
    (lambda f: ".github" in f.parts and "workflows" in f.parts and f.suffix in YAML, [workflow]),
    (lambda f: f.name == "dependabot.yml" and ".github" in f.parts, [dependabot]),
    (lambda f: f.name == ".npmrc", [npmrc]),
    (lambda f: f.name.startswith("Dockerfile") or f.name.endswith(".dockerfile"), [dockerfile]),
    (lambda f: f.suffix in YAML and re.match(r"^(?:docker-)?compose[\w.-]*\.ya?ml$", f.name), [compose]),
    (lambda f: f.suffix in YAML and not re.match(r"^(?:docker-)?compose[\w.-]*\.ya?ml$", f.name), [kubernetes, spring_yaml]),
    (lambda f: f.suffix in (".js", ".ts", ".mjs", ".jsx", ".tsx"), [express_sessions, post_message]),
    (lambda f: f.suffix in (".html", ".htm", ".jinja", ".jinja2", ".j2", ".ejs", ".hbs", ".vue"), [page_assets]),
    (lambda f: f.suffix in (".java", ".properties"), [spring]),
]


def checks_for(f: Path) -> list:
    """The checks that apply to this file, by its name and place."""
    return [check for applies, checks in ROUTES if applies(f) for check in checks]


def findings(f: Path) -> list:
    try:
        return [fx for check in checks_for(f) for fx in check(f)]
    except OSError:
        return []


def root_findings(paths) -> list:
    """Workflows, manifests, compose files, Dockerfiles, .npmrc live anywhere in the tree (.github/, k8s/,
    .devcontainer/, the root): these rules run over the whole project whatever the code roots, skipping only
    what no tool reads; the scan's dedupe drops what a path already covered."""
    if any(Path(r).resolve() == ROOT for r in paths):
        return []
    return [fx for f in _infra_files() for fx in (scan_dockerfile(f) if f.name.startswith("Dockerfile") else []) + findings(f)]


def _infra_files() -> list:
    """Every file under the project these rules apply to, outside the folders no tool reads."""
    skipped = SKIP | {".git"}
    return [f for f in ROOT.rglob("*") if f.is_file() and not (skipped & set(f.relative_to(ROOT).parts)) and checks_for(f)]
