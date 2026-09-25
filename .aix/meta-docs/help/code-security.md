aix code security [PATH...] [--strict] [--gate] [--audit] [--report] [--selftest]

DETERMINISTIC SECURITY SCAN, mapped to the vulnerability register. Every rule names the VUL row it feeds and the
CWE it detects, so a finding is evidence the register can act on. Rules follow bandit, semgrep, gitleaks and
eslint-plugin-security; categories follow the OWASP Top 10 and the seeded register. No dependencies.

What it checks (Python, JS/TS, Rust, Java, plus Dockerfiles, compose, manifests, env files)
  VUL-INJ-001/002    SQL built from strings; shell commands (shell=True, exec/system); eval; template strings;
                     paths from request input                                             CWE-89/78/95/1336/22
  VUL-INPUT-001/002  pickle/marshal/yaml.load without SafeLoader, ObjectInputStream, XML entities  CWE-502/20
  VUL-SECRET-001/002 private keys, cloud/API tokens, hard-coded passwords; TLS verification off; DEBUG on;
                     ALLOWED_HOSTS *                                                       CWE-798/295/489/16
  VUL-AUTHN-001/002  md5/sha1 for passwords, random for tokens; JWT unverified / alg none; cookies without
                     Secure/HttpOnly                                                       CWE-328/338/347/614
  VUL-WEB-001/002/003 innerHTML/dangerouslySetInnerHTML/mark_safe; CSRF disabled; CORS *; open redirect
                                                                                          CWE-79/352/942/601
  VUL-LOG-001        credentials in log/print lines                                        CWE-532
  VUL-AI-001/002     prompts built by interpolation; LLM calls without an output limit      CWE-77/770
  VUL-INFRA-001      chmod 777, privileged containers, Dockerfile without USER              CWE-732/250
  VUL-DEP-001        unpinned requirements, unbounded npm ranges, missing lockfiles, FROM without tag  CWE-1104

  Assembled, then used (every language): a variable takes a string built from a literal plus a value (`+`, f-string,
  .format, template literal, String.format, format!, %) and, within the next 40 lines, is the argument of a dangerous
  call. What the literal looks like picks the sinks: an SQL keyword -> query/execute (CWE-89); a path or path.join ->
  open/fs/File (CWE-22); HTML -> innerHTML/send/Markup (CWE-79); {{ }} -> Template (CWE-1336); http -> requests/fetch/
  URL (CWE-918); any literal -> a shell (CWE-78) or eval (CWE-95). Reported at the call, both lines in the snippet.
  Not a finding: no literal, a reassignment in between (`cmd = shlex.quote(cmd)`), an argument list, spawn without
  shell: true, a callee that is no sink, a value made only of literals and the file's own location (`__dirname`,
  `__file__`, `OUT_DIR`), and build scripts and `scripts/` folders (the developer's own inputs). Shape only, no input
  source: noisier than aix code vulnerabilities by design.

  Never a finding, in every rule: a signature line (`def render_template_string(...)`), a Python docstring line,
  a constant command (`os.system("make")`), `innerHTML = ""` or another node's markup, Rust code under
  `#[cfg(test)]`, a `node`/`npm` entry under `engines`, a published library without a lockfile (the consumer
  locks), a Cargo workspace member (the workspace locks at its root).

How to read it
  A match is a FINDING TO REVIEW, never proof of exploitability; a row with no match is not proven clean. The
  report says both. Findings in test code are listed but not gated (--strict gates them too).
  Reviewed and accepted? Mark the line:   # aix: accepted VUL-INJ-002 <why>   (listed, never hidden)

The important part: --audit
  Writes docs/security/audits/AUDIT-<date>-code.md from .aix/templates/audit-report.md with the findings table filled
  (asset, control, evidence file:line, status before -> "confirmed? review"), and rows for every rule that matched
  nothing ("unverified by scan alone"). That file is the evidence `aix docs validate` and `aix docs security`
  require before a VUL status may change; a human (or the security-audit-* skills) completes the Status column.

Options
  --strict    gate on test-code findings as well      --gate    exit 1 if any finding to review remains
  --audit     write the audit report + INDEX row       --report  write docs/tests/code-security.md
  --selftest  known-vulnerable snippets must be found, safe variants must not
Related: aix docs security (register state), skills security-audit-* (reasoning on the hits), security-threat-model.
