"""Leaf: the static security rules of `aix code security`, each mapped to a row of the vulnerability register
(docs/security/vulnerability-register.md) and a CWE. Regexes run per line with comments stripped; Dockerfiles have
their own two rules. Markers: `# aix: accepted VUL-… why` on a line, `aix: skip-security-scan` in a file's head."""
import re


TEXT_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".rs", ".java", ".kt", ".yml", ".yaml", ".json", ".toml", ".env",
            ".ini", ".cfg", ".conf", ".txt", ".html", ".jinja", ".jinja2", ".j2", ".sh", ".properties", ".xml", ".tf"}
ACCEPT = re.compile(r"aix:\s*accepted\s+(VUL-[A-Z]+-\d{3})(.*)$")
SKIP_FILE = re.compile(r"aix:\s*skip-security-scan\b(.*)$")   # in the first MARKER_LINES lines: whole file skipped, listed as such
MARKER_LINES = 30

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
     r"(?:subprocess\.\w+\([^)]*shell\s*=\s*True|\b(?:os\.system|os\.popen|commands\.getoutput)\((?!\s*[\"'][^\"'+%{]*[\"']\s*\)))",
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
     r"(?:\.(?:innerHTML|outerHTML)\s*=(?!=)(?!\s*[\"'][^\"']*[\"']\s*;?\s*$)(?!\s*`[^`$]*`\s*;?\s*$)(?!\s*[\w.]+\.(?:outerHTML|innerHTML)\s*;?\s*$)|document\.write\(|dangerouslySetInnerHTML|v-html=|insertAdjacentHTML\()",
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


# taint advice per CWE, shared by the Python and JS/TS taint leaves
ADVICE = {"CWE-78": "argument list without a shell; validate each argument", "CWE-95": "never eval input; a dispatch table or ast.literal_eval",
          "CWE-89": "parameterised query: execute(sql, params)", "CWE-22": "resolve against a base directory and reject anything outside it",
          "CWE-601": "allow-list targets or relative paths only", "CWE-1336": "render a file template with a context",
          "CWE-502": "json / yaml.safe_load; never deserialise input", "CWE-918": "allow-list hosts; block private ranges and redirects",
          "CWE-79": "escape on output (textContent, the template engine's auto-escape); never build HTML from input"}
