#!/usr/bin/env python3
"""aix code security — deterministic static checks mapped to the vulnerability register, producing audit evidence.

Every rule names the VUL row it feeds and the CWE it detects. A match is a FINDING TO REVIEW, never proof of
exploitability; a clean scan is not proof of absence. Rules follow bandit, semgrep, gitleaks and
eslint-plugin-security; categories follow the OWASP Top 10 and the seeded register.

Suppress a reviewed finding in place with a comment on the same line:  # aix: accepted VUL-INJ-002 <why>
Suppressions are listed, never hidden. `--audit` writes docs/security/audits/AUDIT-<date>-code.md with the findings
table filled in: the evidence `aix docs security` requires before a status may change.
aix: skip-security-scan this file holds the rule patterns and the known-bad self-test snippets"""
import ast, re, sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import ROOT, CODE_ROOTS, SKIP, rel

TEXT_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".rs", ".java", ".kt", ".yml", ".yaml", ".json", ".toml", ".env",
            ".ini", ".cfg", ".conf", ".txt", ".html", ".jinja", ".jinja2", ".j2", ".sh", ".properties", ".xml", ".tf"}
ACCEPT = re.compile(r"aix:\s*accepted\s+(VUL-[A-Z]+-\d{3})(.*)$")
SKIP_FILE = re.compile(r"aix:\s*skip-security-scan\b(.*)$")   # in the first 12 lines: whole file skipped, listed as such

# (vul, cwe, title, languages or {"*"}, regex, advice)   regexes run per line, comments stripped first
RULES = [
    # --- injection --------------------------------------------------------------------------------------------
    ("VUL-INJ-001", "CWE-89", "SQL built from strings", {"py"},
     r"\.(?:execute|executemany|raw|executescript)\(\s*(?:f['\"]|['\"][^'\"]*['\"]\s*(?:%|\+|\.format\()|[A-Za-z_]\w*\s*(?:%|\+)\s*)",
     "parameterise: cursor.execute(sql, params); never interpolate values into SQL"),
    ("VUL-INJ-001", "CWE-89", "SQL built from strings", {"js"},
     r"\.(?:query|execute|raw)\(\s*(?:`[^`]*\$\{|['\"][^'\"]*['\"]\s*\+)",
     "use placeholders ($1 / ?) with a parameter array; never a template literal with user values"),
    ("VUL-INJ-001", "CWE-89", "SQL built from strings", {"java"},
     r"(?:createQuery|createNativeQuery|executeQuery|executeUpdate|execute|prepareStatement)\(\s*\"[^\"]*\"\s*\+",
     "PreparedStatement with ? placeholders; never concatenate values into the statement"),
    ("VUL-INJ-002", "CWE-78", "OS command with a shell", {"py"},
     r"(?:subprocess\.\w+\([^)]*shell\s*=\s*True|\bos\.system\(|\bos\.popen\(|commands\.getoutput\()",
     "subprocess.run([...], shell=False) with an argument list; validate each argument"),
    ("VUL-INJ-002", "CWE-78", "OS command with a shell", {"js"},
     r"(?:child_process\.)?\b(?:exec|execSync)\(\s*(?:`[^`]*\$\{|['\"][^'\"]*['\"]\s*\+|[A-Za-z_]\w*\s*[+`])",
     "execFile/spawn with an argument array; never build a shell string from input"),
    ("VUL-INJ-002", "CWE-78", "OS command with a shell", {"java"},
     r"Runtime\.getRuntime\(\)\.exec\(\s*(?:\"[^\"]*\"\s*\+|[A-Za-z_]\w*\s*\+)",
     "ProcessBuilder with a list of arguments; validate each"),
    ("VUL-INJ-002", "CWE-95", "eval / exec of dynamic code", {"py"},
     r"(?<![\w.])(?:eval|exec)\(\s*(?!['\"])[A-Za-z_(]", "no eval/exec on data; use ast.literal_eval for literals, a dispatch table for names"),
    ("VUL-INJ-002", "CWE-95", "eval / dynamic Function", {"js"},
     r"(?<![\w.])(?:eval|new\s+Function)\(\s*(?!['\"])", "no eval; JSON.parse for data, a lookup table for names"),
    ("VUL-INJ-002", "CWE-1336", "server-side template built from strings", {"py"},
     r"(?:render_template_string|Template)\(\s*(?:f['\"]|['\"][^'\"]*['\"]\s*(?:%|\+|\.format\()|[A-Za-z_]\w*\s*(?:%|\+))",
     "render a file template with a context; never a template string built from input"),
    ("VUL-INJ-002", "CWE-22", "path from input without normalisation", {"py"},
     r"(?:open|send_file|send_from_directory|os\.remove|shutil\.\w+)\(\s*(?:request\.|params\.|args\.|form\.)",
     "resolve against a base directory and reject anything outside it (Path.resolve, is_relative_to)"),
    # --- deserialisation / input -----------------------------------------------------------------------------
    ("VUL-INPUT-002", "CWE-502", "unsafe deserialisation", {"py"},
     r"(?:\bpickle\.loads?\(|\bmarshal\.loads?\(|\bshelve\.open\(|yaml\.load\((?![^)]*Loader\s*=\s*(?:yaml\.)?(?:Safe|CSafe|Base)Loader)(?![^)]*safe)|\bjsonpickle\.decode\()",
     "json or yaml.safe_load; never unpickle data you did not produce"),
    ("VUL-INPUT-002", "CWE-502", "unsafe deserialisation", {"java"},
     r"new\s+ObjectInputStream\(|\.readObject\(\)|XMLDecoder\(", "allow-list classes via ObjectInputFilter, or use JSON"),
    ("VUL-INPUT-002", "CWE-502", "unsafe deserialisation", {"js"},
     r"(?:node-serialize|serialize-javascript)|\bunserialize\(", "JSON.parse; never unserialize untrusted data"),
    ("VUL-INPUT-001", "CWE-20", "XML parsed with external entities possible", {"py"},
     r"(?:xml\.etree|xml\.dom\.minidom|xml\.sax|lxml\.etree)\.(?:parse|fromstring|XMLParser)\(", "defusedxml, or disable entity resolution"),
    # --- secrets & config ------------------------------------------------------------------------------------
    ("VUL-SECRET-001", "CWE-798", "private key in repository", {"*"},
     r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY", "remove, rotate the key, load from a secret store"),
    ("VUL-SECRET-001", "CWE-798", "cloud / API token literal", {"*"},
     r"(?:AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{22,}|xox[baprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9]{32,}|sk-ant-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{35})",
     "revoke and rotate now; read it from the environment or a secret manager"),
    ("VUL-SECRET-001", "CWE-798", "hard-coded password / secret literal", {"*"},
     r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|private[_-]?key)\b\s*[:=]\s*['\"][^'\"$%{}<>\s]{6,}['\"]",
     "load from the environment / secret manager; a literal in code is in every clone and every log of the repo"),
    ("VUL-SECRET-002", "CWE-295", "TLS verification disabled", {"*"},
     r"(?:verify\s*=\s*False|_create_unverified_context|rejectUnauthorized\s*:\s*false|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0|InsecureSkipVerify\s*:\s*true|danger_accept_invalid_certs\(\s*true|TrustAllCerts|setHostnameVerifier\(\s*\(?[^)]*true)",
     "verify certificates; pin or supply the CA bundle instead of disabling verification"),
    ("VUL-SECRET-002", "CWE-489", "debug mode on", {"py", "js"},
     r"(?:\bDEBUG\s*=\s*True\b|\.run\([^)]*debug\s*=\s*True|app\.debug\s*=\s*True)", "debug from the environment, off by default; never in production config"),
    ("VUL-SECRET-002", "CWE-16", "wildcard hosts", {"py"},
     r"ALLOWED_HOSTS\s*=\s*\[\s*['\"]\*['\"]", "list the real hostnames"),
    # --- auth ----------------------------------------------------------------------------------------------------
    ("VUL-AUTHN-001", "CWE-328", "weak hash for passwords / tokens", {"py"},
     r"hashlib\.(?:md5|sha1)\(", "passwords: argon2/bcrypt/scrypt; integrity: sha256+; md5/sha1 only for non-security checksums (mark it)"),
    ("VUL-AUTHN-001", "CWE-328", "weak hash", {"java"},
     r"MessageDigest\.getInstance\(\s*\"(?:MD5|SHA-?1)\"", "PBKDF2/bcrypt/argon2 for passwords; SHA-256+ elsewhere"),
    ("VUL-AUTHN-001", "CWE-328", "weak hash", {"js"},
     r"createHash\(\s*['\"](?:md5|sha1)['\"]", "bcrypt/argon2 for passwords; sha256+ elsewhere"),
    ("VUL-AUTHN-001", "CWE-338", "non-cryptographic randomness for a secret", {"py"},
     r"\brandom\.(?:random|randint|choice|choices|getrandbits|randrange)\([^\n]*(?i:token|secret|password|salt|nonce|otp|session|key)|(?i:token|secret|password|salt|nonce|otp|session|key)[^\n]*=\s*[^\n]*\brandom\.(?:random|randint|choice|choices|getrandbits|randrange)\(",
     "secrets.token_bytes / token_urlsafe / SystemRandom"),
    ("VUL-AUTHN-001", "CWE-338", "non-cryptographic randomness for a secret", {"js"},
     r"(?i:token|secret|password|salt|nonce|otp|session)[^\n]*Math\.random\(", "crypto.randomBytes / crypto.getRandomValues"),
    ("VUL-AUTHN-001", "CWE-338", "non-cryptographic randomness for a secret", {"java"},
     r"new\s+Random\(\)[^\n]*(?i:token|secret|password|salt|nonce|otp|session)|(?i:token|secret|password|salt|nonce|otp|session)[^\n]*new\s+Random\(\)", "SecureRandom"),
    ("VUL-AUTHN-002", "CWE-347", "JWT signature not verified / alg none", {"*"},
     r"(?:verify_signature['\"]?\s*:\s*False|verify\s*=\s*False[^\n]*jwt|jwt\.decode\([^)]*verify\s*=\s*False|algorithms?\s*[:=]\s*\[?\s*['\"]none['\"]|\.decode\([^)]*\)\s*#\s*noverify)",
     "always verify with the expected algorithm list; reject alg=none"),
    ("VUL-AUTHN-002", "CWE-614", "cookie without Secure / HttpOnly", {"py", "js"},
     r"(?:set_cookie\([^)]*(?:secure\s*=\s*False|httponly\s*=\s*False)|cookie\([^)]*(?:secure\s*:\s*false|httpOnly\s*:\s*false)|SESSION_COOKIE_SECURE\s*=\s*False|SESSION_COOKIE_HTTPONLY\s*=\s*False)",
     "Secure, HttpOnly and SameSite on session cookies"),
    # --- web -----------------------------------------------------------------------------------------------------
    ("VUL-WEB-001", "CWE-79", "HTML injected without escaping", {"js"},
     r"(?:\.innerHTML\s*=|\.outerHTML\s*=|document\.write\(|dangerouslySetInnerHTML|v-html=|insertAdjacentHTML\()",
     "textContent / framework bindings; if HTML is required, sanitise (DOMPurify) first"),
    ("VUL-WEB-001", "CWE-79", "HTML marked safe", {"py"},
     r"(?:\bmark_safe\(|\bMarkup\(|\|\s*safe\b|autoescape\s*=\s*False|render_template_string\()", "let the template engine escape; sanitise (bleach) before marking safe"),
    ("VUL-WEB-002", "CWE-352", "CSRF protection disabled", {"py", "js"},
     r"(?:@csrf_exempt|csrf_exempt\(|WTF_CSRF_ENABLED\s*=\s*False|CSRF_ENABLED\s*=\s*False|csrf\s*:\s*false|ignoreMethods\s*:\s*\[)",
     "keep CSRF protection on state-changing routes; use SameSite cookies + tokens"),
    ("VUL-WEB-003", "CWE-942", "CORS open to any origin", {"*"},
     r"(?:allow_origins\s*=\s*\[\s*['\"]\*['\"]|Access-Control-Allow-Origin['\"]?\s*[:,]\s*['\"]\*|origin\s*:\s*['\"]\*['\"]|origins\s*=\s*['\"]\*['\"]|CORS_ORIGIN_ALLOW_ALL\s*=\s*True|allowedOrigins\(\s*\"\*\")",
     "list the real origins; never * together with credentials"),
    ("VUL-WEB-003", "CWE-601", "open redirect from input", {"py", "js"},
     r"(?:redirect\(\s*(?:request\.(?:args|GET|params|form|query)|req\.(?:query|params|body)))", "allow-list redirect targets or use relative paths only"),
    # --- logging -------------------------------------------------------------------------------------------------
    ("VUL-LOG-001", "CWE-532", "secret in a log line", {"*"},
     r"(?:log(?:ger|ging)?\.\w+|console\.\w+|print|System\.out\.print\w*)\([^\n]*(?i:password|passwd|secret|token|api_key|apikey|authorization|credit_card)",
     "log identifiers, never credentials; redact before logging"),
    # --- AI / LLM ------------------------------------------------------------------------------------------------
    ("VUL-AI-001", "CWE-77", "prompt built by string interpolation", {"py", "js"},
     r"(?i:prompt|system|instruction)\w*\s*[:=]\s*(?:f['\"]|['\"][^'\"]*['\"]\s*(?:\+|%|\.format\()|`[^`]*\$\{)",
     "separate roles: untrusted text goes in a user/tool message, never in the system prompt; delimit and label it"),
    ("VUL-AI-002", "CWE-770", "LLM call without an output limit", {"py", "js"},
     r"\.(?:create|generate|complete|chat)\((?![^)]*max_?(?:tokens|output_tokens|completion_tokens))[^)]*(?:model\s*[:=]|messages\s*[:=])",
     "set max_tokens / max_output_tokens and a timeout; budget per request"),
    # --- infra -----------------------------------------------------------------------------------------------------
    ("VUL-INFRA-001", "CWE-732", "world-writable permissions", {"*"},
     r"(?:(?:^\s*|RUN\s+|&&\s*|;\s*|sudo\s+)chmod\s+(?:-R\s+)?[0-7]?777\b|os\.chmod\([^)]*0o777|\.chmod\(\s*0o777)", "least privilege: 0o640/0o750 and a dedicated user"),
    ("VUL-INFRA-001", "CWE-250", "privileged container", {"*"},
     r"(?:privileged\s*:\s*true|--privileged\b|network_mode\s*:\s*['\"]?host)", "drop privileges; add only the capabilities needed"),
]
DOCKER_RULES = [
    ("VUL-INFRA-001", "CWE-250", "container runs as root (no USER)", "add a non-root USER before the entrypoint"),
    ("VUL-DEP-001", "CWE-1104", "base image without a pinned tag", "pin FROM image:tag@sha256:... or at least a version tag, never :latest / untagged"),
]
LANG = {".py": "py", ".js": "js", ".jsx": "js", ".ts": "js", ".tsx": "js", ".mjs": "js", ".rs": "rust", ".java": "java", ".kt": "java"}


# ---- scanning -----------------------------------------------------------------------------------------------------

def is_test(p: Path) -> bool:
    return any(part in ("tests", "test", "__tests__", "fixtures") for part in p.parts) or p.name.startswith("test_") \
        or ".test." in p.name or ".spec." in p.name


def strip_comment(line: str, lang: str) -> str:
    if lang == "py" or lang is None:
        return re.sub(r"(?<!['\"])#.*$", "", line) if lang == "py" else line
    return re.sub(r"//.*$|/\*.*?\*/", "", line)


def scan_file(f: Path):
    """[(vul, cwe, title, file, line_no, snippet, advice, accepted)]"""
    lang = LANG.get(f.suffix)
    langs = {lang, "*"} if lang else {"*"}
    out = []
    try:
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return out
    for raw in lines[:12]:
        m = SKIP_FILE.search(raw)
        if m:
            return [("SKIPPED", "", "file skipped by marker", rel(f), 1, "aix: skip-security-scan " + m.group(1).strip(), "", "skip")]
    for i, raw in enumerate(lines, 1):
        acc = ACCEPT.search(raw)
        code = strip_comment(raw, lang)
        for vul, cwe, title, rlangs, rx, advice in RULES:
            if not (rlangs & langs):
                continue
            if re.search(rx, code):
                accepted = acc.group(1) + acc.group(2).strip() if acc and acc.group(1) == vul else None
                out.append((vul, cwe, title, rel(f), i, raw.strip()[:110], advice, accepted))
    return out


def scan_dockerfile(f: Path):
    text = f.read_text(encoding="utf-8", errors="replace")
    out = []
    if re.search(r"^\s*FROM\b", text, re.M) and not re.search(r"^\s*USER\s+(?!root\b)\w", text, re.M):
        out.append(("VUL-INFRA-001", "CWE-250", DOCKER_RULES[0][2], rel(f), 1, "no USER instruction", DOCKER_RULES[0][3], None))
    for m in re.finditer(r"^\s*FROM\s+([^\s]+)", text, re.M):
        image = m.group(1)
        if image.lower() not in ("scratch",) and not re.search(r"@sha256:|:[\w.-]+$", image) or image.endswith(":latest"):
            out.append(("VUL-DEP-001", "CWE-1104", DOCKER_RULES[1][2], rel(f), text.count("\n", 0, m.start()) + 1, m.group(0).strip(), DOCKER_RULES[1][3], None))
    return out


def scan_dependencies(root: Path):
    """Unpinned dependency declarations and missing lockfiles (VUL-DEP-001)."""
    out = []
    for f in root.rglob("requirements*.txt"):
        if any(s in f.parts for s in SKIP):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            s = line.split("#")[0].strip()
            if s and not s.startswith(("-", "git+", "http")) and "==" not in s and "@" not in s:
                out.append(("VUL-DEP-001", "CWE-1104", "unpinned dependency", rel(f), i, s, "pin exact versions (==) or use a lockfile (uv/poetry/pip-tools)", None))
    for f in root.rglob("package.json"):
        if any(s in f.parts for s in SKIP):
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r'"([^"]+)"\s*:\s*"(\*|latest|>=?[^"]*|x)"', text):
            out.append(("VUL-DEP-001", "CWE-1104", "unbounded dependency range", rel(f), text.count("\n", 0, m.start()) + 1, m.group(0), "use ^/~ ranges with a committed lockfile, or exact versions", None))
        if not any((f.parent / l).exists() for l in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb")):
            out.append(("VUL-DEP-001", "CWE-1104", "no lockfile next to package.json", rel(f), 1, "package.json without lockfile", "commit package-lock.json / pnpm-lock.yaml so builds are reproducible", None))
    for f in root.rglob("pyproject.toml"):
        if any(s in f.parts for s in SKIP):
            continue
        if re.search(r"^\s*(?:dependencies|requires)\s*=", f.read_text(encoding="utf-8", errors="replace"), re.M) and \
                not any((f.parent / l).exists() for l in ("uv.lock", "poetry.lock", "pdm.lock", "requirements.txt", "requirements.lock")):
            out.append(("VUL-DEP-001", "CWE-1104", "no lockfile next to pyproject.toml", rel(f), 1, "pyproject without uv.lock/poetry.lock", "commit a lockfile so builds are reproducible", None))
    for f in root.rglob("Cargo.toml"):
        if any(s in f.parts for s in SKIP) or (f.parent / "Cargo.lock").exists() or not re.search(r"^\[dependencies\]", f.read_text(encoding="utf-8", errors="replace"), re.M):
            continue
        out.append(("VUL-DEP-001", "CWE-1104", "no Cargo.lock", rel(f), 1, "Cargo.toml without Cargo.lock", "commit Cargo.lock", None))
    return out


def scan(paths):
    findings = []
    for root in paths:
        base = (ROOT / root) if not Path(root).is_absolute() else Path(root)
        if not base.exists():
            continue
        files = [base] if base.is_file() else base.rglob("*")
        for f in files:
            inner = f.relative_to(base).parts if base.is_dir() else ()
            if not f.is_file() or any(s in inner for s in SKIP):
                continue
            if f.name.startswith("Dockerfile") or f.name.endswith(".dockerfile"):
                findings += scan_dockerfile(f)
            elif f.suffix in TEXT_EXT or f.name in (".env", ".env.local", ".env.production"):
                if f.name == ".env.example":
                    continue
                findings += scan_file(f)
    for root in {ROOT} | {(ROOT / r) for r in paths if (ROOT / r).is_dir()}:
        findings += scan_dependencies(root)
    seen, out = set(), []
    for fx in findings:
        key = (fx[0], fx[3], fx[4], fx[2])
        if key not in seen:
            seen.add(key); out.append(fx)
    return out


# ---- reporting ----------------------------------------------------------------------------------------------------

def register_rows():
    reg = ROOT / "docs" / "security" / "vulnerability-register.md"
    rows = {}
    if reg.exists():
        for line in reg.read_text(encoding="utf-8").splitlines():
            if line.startswith("| VUL-"):
                c = [x.strip() for x in line.strip("|").split("|")]
                rows[c[0]] = (c[1], c[3])
    return rows


def render(findings, paths, strict):
    rows = register_rows()
    by_vul = defaultdict(list)
    for fx in findings:
        by_vul[fx[0]].append(fx)
    covered = sorted({r[0] for r in RULES} | {r[0] for r in DOCKER_RULES})
    skipped = [fx for fx in findings if fx[0] == "SKIPPED"]
    findings = [fx for fx in findings if fx[0] != "SKIPPED"]
    by_vul = defaultdict(list)
    for fx in findings:
        by_vul[fx[0]].append(fx)
    live = [fx for fx in findings if not fx[7] and (strict or not is_test(ROOT / fx[3]))]
    tests = [fx for fx in findings if not fx[7] and is_test(ROOT / fx[3])]
    accepted = [fx for fx in findings if fx[7]]
    lines = [f"Code security — {', '.join(paths)}", "",
             f"  findings to review {len(live)}" + (f"; in tests (not gated, --strict to gate) {len(tests)}" if tests else "") + (f"; accepted in code {len(accepted)}" if accepted else "")
             + f"; register rows with rules {len(covered)}, with findings {len(by_vul)}",
             "  A match is a finding to review, not proof of exploitability; a clean row is not proof of absence.", ""]
    for vul in sorted(by_vul, key=lambda v: (-len([f for f in by_vul[v] if not f[7]]), v)):
        desc, status = rows.get(vul, ("(not in register)", "?"))
        lines.append(f"  {vul}  {desc[:70]}  [register: {status}]")
        for _, cwe, title, file, ln, snippet, advice, acc in sorted(by_vul[vul], key=lambda x: (x[3], x[4]))[:25]:
            tag = "accepted: " + acc if acc else ("test" if is_test(ROOT / file) else "REVIEW")
            lines.append(f"    {file}:{ln}  {title} ({cwe})  [{tag}]")
            lines.append(f"      {snippet}")
            if not acc:
                lines.append(f"      -> {advice}")
        if len(by_vul[vul]) > 25:
            lines.append(f"    ... {len(by_vul[vul]) - 25} more")
        lines.append("")
    for fx in skipped:
        lines.append(f"  skipped by marker: {fx[3]}  ({fx[5]})")
    clean = [v for v in covered if v not in by_vul]
    lines.append("  no pattern matched for: " + ", ".join(clean) + "  (rules ran; absence of a match is not evidence of absence)")
    lines.append("  next: review each REVIEW line; fix or mark `# aix: accepted VUL-… <why>`; `aix code security --audit` writes the audit report;")
    lines.append("        then `aix docs security` / the security-audit-* skills move register rows on that evidence.")
    return "\n".join(lines), len(live)


def write_audit(findings, paths):
    findings = [fx for fx in findings if fx[0] != "SKIPPED"]
    rows = register_rows()
    today = date.today().isoformat()
    out = ROOT / "docs" / "security" / "audits" / f"AUDIT-{today}-code.md"
    by_vul = defaultdict(list)
    for fx in findings:
        by_vul[fx[0]].append(fx)
    covered = sorted({r[0] for r in RULES} | {r[0] for r in DOCKER_RULES})
    body = [f"---\nid: AUDIT-{today}-code\nskill: aix code security (deterministic scan)\ndate: {today}\nscope: [{', '.join(paths)}]\nresult: {'findings' if any(not f[7] for f in findings) else 'pass'}\n---",
            f"# Audit — code scan — {today}", "",
            "## Method (what was checked, tools run)",
            f"`aix code security` static rules ({len(RULES)} line rules + Dockerfile + dependency manifests) mapped to VUL rows and CWEs. "
            "A match is a finding to review; a clean row means no pattern matched, not absence. Human review recorded in the Status column.", "",
            "## Findings",
            "| VUL id | Asset / threat | Impact | Likelihood rationale | Control | Verification method | Evidence | Status before → after | Residual risk |",
            "|---|---|---|---|---|---|---|---|---|"]
    for vul in sorted(by_vul):
        desc, status = rows.get(vul, ("", "?"))
        for _, cwe, title, file, ln, snippet, advice, acc in sorted(by_vul[vul], key=lambda x: (x[3], x[4])):
            ev = f"`{file}:{ln}` {title} ({cwe})"
            after = "accepted (in code)" if acc else "confirmed? review"
            body.append(f"| {vul} | {desc[:50]} | | static match | {advice[:60]} | code review | {ev} | {status} → {after} | |")
    for vul in [v for v in covered if v not in by_vul]:
        desc, status = rows.get(vul, ("", "?"))
        body.append(f"| {vul} | {desc[:50]} | | no static match | | static scan | no pattern matched | {status} → {status} (unverified by scan alone) | |")
    body += ["", "## New vulnerabilities discovered (added to register)", "- none by this scan (static rules only match seeded categories)", "",
             "## Follow-ups (tasks created)", "- review every `confirmed? review` row; fix or accept with rationale", ""]
    out.write_text("\n".join(body), encoding="utf-8")
    idx = out.parent / "INDEX.md"
    if idx.exists() and out.name not in idx.read_text(encoding="utf-8"):
        with idx.open("a", encoding="utf-8") as fh:
            fh.write(f"| `{out.name}` | Deterministic code scan (`aix code security`), {len(findings)} findings, {len(covered)} rows checked | Verifying VUL statuses; release |\n")
    return out


# ---- self-test ------------------------------------------------------------------------------------------------------

SELFTEST = {
    "bad.py": '''import subprocess, pickle, hashlib, random, yaml
def run(cmd): return subprocess.run(cmd, shell=True)
def load(b): return pickle.loads(b)
def cfg(s): return yaml.load(s)
def safe(s): return yaml.load(s, Loader=yaml.SafeLoader)
def q(cur, name): cur.execute("SELECT * FROM t WHERE n = '%s'" % name)
def ok(cur, name): cur.execute("SELECT * FROM t WHERE n = ?", (name,))
password = "hunter2xyz"
token = random.randint(0, 99999)
h = hashlib.md5(b"x")  # aix: accepted VUL-AUTHN-001 checksum only
DEBUG = True
''',
    "bad.ts": '''const q = (db: any, id: string) => db.query(`SELECT * FROM t WHERE id = ${id}`);
el.innerHTML = user;
const token = "t" + Math.random();
fetch(u, { rejectUnauthorized: false });
''',
    "Dockerfile": "FROM python\nRUN pip install x\nCMD [\"python\", \"app.py\"]\n",
    "requirements.txt": "flask\nrequests==2.31.0\n",
}


def selftest():
    import tempfile
    global ROOT
    with tempfile.TemporaryDirectory() as d:
        base = Path(d)
        for name, text in SELFTEST.items():
            (base / name).write_text(text, encoding="utf-8")
        saved, ROOT = ROOT, base
        try:
            found = scan([str(base)])
        finally:
            ROOT = saved
    got = defaultdict(int)
    for vul, cwe, title, file, ln, snippet, advice, acc in found:
        got[(vul, Path(file).name, "acc" if acc else "open")] += 1
    want = [("VUL-INJ-002", "bad.py", "open", 1), ("VUL-INPUT-002", "bad.py", "open", 2), ("VUL-INJ-001", "bad.py", "open", 1),
            ("VUL-SECRET-001", "bad.py", "open", 1), ("VUL-AUTHN-001", "bad.py", "open", 1), ("VUL-AUTHN-001", "bad.py", "acc", 1),
            ("VUL-SECRET-002", "bad.py", "open", 1), ("VUL-INJ-001", "bad.ts", "open", 1), ("VUL-WEB-001", "bad.ts", "open", 1),
            ("VUL-AUTHN-001", "bad.ts", "open", 1), ("VUL-SECRET-002", "bad.ts", "open", 1), ("VUL-INFRA-001", "Dockerfile", "open", 1),
            ("VUL-DEP-001", "Dockerfile", "open", 1), ("VUL-DEP-001", "requirements.txt", "open", 1)]
    failed = 0
    for vul, file, state, n in want:
        ok = got[(vul, file, state)] == n; failed += not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {vul} in {file} ({state}): {got[(vul, file, state)]} (expected {n})")
    safe_hits = [f for f in found if f[4] in (5, 7) and Path(f[3]).name == "bad.py"]
    ok = not safe_hits; failed += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  safe yaml.load(Loader=SafeLoader) and parameterised execute not flagged")
    print("selftest: " + ("all passed" if not failed else f"{failed} FAILED"))
    sys.exit(1 if failed else 0)


USAGE = "usage: aix code security [PATH...] [--strict] [--gate] [--audit] [--report] [--selftest]"


def main(args):
    if "--selftest" in args:
        return selftest()
    strict, gate, audit, report = "--strict" in args, "--gate" in args, "--audit" in args, "--report" in args
    paths = [a for a in args if not a.startswith("--")] or [r for r in CODE_ROOTS if (ROOT / r).exists()] or ["."]
    findings = scan(paths)
    text, n_live = render(findings, paths, strict)
    print(text)
    if report:
        out = ROOT / "docs" / "tests" / "code-security.md"
        out.write_text("# Code security (generated — do not edit)\n\n```\n" + text + "\n```\n", encoding="utf-8")
        print(f"\n  wrote {out.relative_to(ROOT)}")
    if audit:
        print(f"\n  wrote {write_audit(findings, paths).relative_to(ROOT)}  (fill Status per row after review; aix docs security reads it)")
    if gate and n_live:
        sys.exit(f"GATE FAILED: {n_live} security finding(s) to review")
    findings = [fx for fx in findings if fx[0] != "SKIPPED"]
    if gate:
        print("GATE PASSED")


if __name__ == "__main__":
    main(sys.argv[1:])
