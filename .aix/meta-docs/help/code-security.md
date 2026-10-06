aix code security [PATH...] [--strict] [--gate] [--audit] [--report] [--selftest]      aix code security --push [--gate]

DETERMINISTIC SECURITY SCAN, mapped to the vulnerability register. Every rule names the VUL row it feeds and the
CWE it detects, so a finding is evidence the register can act on. Rules follow bandit, semgrep, gitleaks and
eslint-plugin-security; categories follow the OWASP Top 10 and the seeded register. No dependencies.

What it checks (Python, JS/TS, Rust, Java, plus Dockerfiles, compose, manifests, env files)
  VUL-INJ-001/002    SQL built from strings; shell commands (shell=True, exec/system); eval; template strings;
                     paths from request input                                             CWE-89/78/95/1336/22
  VUL-INPUT-001/002  pickle/marshal/yaml.load without SafeLoader, ObjectInputStream, XML entities  CWE-502/20
  VUL-SECRET-001/002 private keys, cloud/API tokens, hard-coded passwords, plus the gitleaks rule set (221
                     provider patterns and a generic one: keyword gate, regex, entropy floor, allowlists for
                     placeholders and example values; secrets by file name such as .p12); TLS verification off;
                     DEBUG on; ALLOWED_HOSTS *                                          CWE-798/295/489/16
  VUL-AUTHN-001/002  md5/sha1 for passwords; java.util.Random / Math.random; DES, RC4 and ECB ciphers; JWT
                     unverified / alg none; cookies without Secure/HttpOnly, setSecure(false)  CWE-328/338/327/347/614
  VUL-WEB-001/002/003 innerHTML/dangerouslySetInnerHTML/mark_safe; CSRF disabled; CORS *; open redirect
                                                                                          CWE-79/352/942/601
  VUL-LOG-001        credentials in log/print lines                                        CWE-532
  VUL-AI-001/002     prompts built by interpolation; LLM calls without an output limit      CWE-77/770
  VUL-INFRA-001      chmod 777, privileged containers, Dockerfile without USER              CWE-732/250
  VUL-DEP-001        unpinned requirements, unbounded npm ranges, missing lockfiles (a workspace root's lockfile,
                     pnpm/Yarn/npm/uv, covers the apps inside it), FROM without tag                 CWE-1104

  Infrastructure and frameworks (file-level rules, the categories a semgrep run adds; .github/ and the root's own
  files are scanned whatever the code roots): GitHub Actions `uses:` pinned to a tag instead of a commit SHA
  (CWE-829), an outsider-written context (`github.event.pull_request.title`, `head_ref`, `ref_name`, `inputs.*`)
  pasted into `run:` (CWE-78), `curl | sh` (CWE-494); dependabot updates without `cooldown:` and .npmrc without
  `min-release-age` (CWE-1104); `RUN sudo` in a Dockerfile, Kubernetes containers without `runAsNonRoot: true` or
  `allowPrivilegeEscalation: false`, compose services with an image but no `no-new-privileges` or `read_only`
  (CWE-250/732); express `session({...})` / `cookieSession({...})` without httpOnly, secure, domain, path, maxAge
  or a name (CWE-614) and with a literal `secret:` (CWE-798); `<script src>` / `<link href>` from another host
  without `integrity=` (CWE-353); Spring `management.endpoints.web.exposure.include=*` (CWE-16) and a method-level
  `@RequestMapping` without `method =` (CWE-352); `postMessage(x, "*")` (CWE-345).

  From the Checkov comparison (2.21.42, benchmark section 19): a workflow with no `permissions:` block at the top or
  in every job runs with the repository's default token (CWE-250), and `permissions: write-all` is named as such; a
  Kubernetes container without `readOnlyRootFilesystem: true` (CWE-732), without `capabilities: drop: [ALL]`, without
  a `seccompProfile` of `RuntimeDefault` or `Localhost` on the container or the pod (CWE-250); an `image:` in a manifest
  with no tag, `:latest`, and no digest (CWE-1104); `chpasswd`, `passwd` or `usermod -p` in a Dockerfile `RUN`
  (CWE-798, a password baked into the image).

  Spring Security and the Java platform (2.21.32): `csrf().disable()` in its three syntaxes (CWE-352) and
  `headers().disable()` (CWE-693); `@CrossOrigin` with no origin or `"*"`, `allowedOrigins("*")`, `addAllowedOrigin("*")`
  (CWE-942); `anyRequest().permitAll()` (CWE-285); `httpBasic(` in a filter chain whose method never calls
  `requiresSecure()` (CWE-319); a `DocumentBuilderFactory` / `SAXParserFactory` / `XMLInputFactory` / `TransformerFactory`
  created in a method that never sets `disallow-doctype-decl`, `ACCESS_EXTERNAL_DTD` or the external-entities feature
  (CWE-611, reported at the factory line); `spring.h2.console.enabled=true`, `server.error.include-stacktrace=always`
  (CWE-489) in properties and YAML; a string literal of 8+ characters as the key of `signWith`, `setSigningKey`,
  `Keys.hmacShaKeyFor`, `new SecretKeySpec` (CWE-798); an empty `checkServerTrusted`, `getAcceptedIssuers` returning
  null, a hostname verifier returning true, `NoopHostnameVerifier`, `TrustAllStrategy` (CWE-295).

  Ownership on `{id}` handlers, Java (2.21.36, VUL-AUTHZ-001, CWE-639): a web handler that takes an id from the URL
  (`@PathVariable`, `@PathParam`) and loads, builds or changes a thing that belongs to a user (a class with a
  user-typed field or an owner id: `private User user`, `userId`, `ownerId`, `tenantId`), with nothing on the way
  tying it to the caller: no `@PreAuthorize`/`@Secured`/`@RolesAllowed` on the method or its class, no principal
  read (`getCurrentUserLogin`, `getAuthentication`, a `Principal` parameter, `@AuthenticationPrincipal`), no
  owner-aware repository method (`findByIdAndUser…`, `…IsCurrentUser`), no owner comparison (`.getUser()`,
  `.getOwner()`), in the handler or in the service method it calls one level down. Not a finding: a project with no
  authentication (no security dependency in the build, no security configuration), a thing without an owner, an
  annotated handler. Ownership is followed one hop through a single-valued field (an operation of a bank account of
  a user: "owned through its bankAccount"), never through a collection and never two hops away.

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

Push protection, before the push: --push
  GitHub and Azure DevOps read every file of a push with provider patterns (Google, AWS, GitHub, Slack, Stripe,
  private keys, JWTs, ...) and refuse the push on a match, whatever the string opens and wherever it sits: no
  marker, test folder or comment is spared. `--push` reads every tracked file the same way (the provider rules of
  the gitleaks set, the generic password rules left out) and lists what such a scanner would refuse; `--gate`
  fails on any. The step `push` is required by the release policy and advised by the standard one.

Options
  --strict    gate on test-code findings as well      --gate    exit 1 if any finding to review remains
  --audit     write the audit report + INDEX row       --report  write docs/tests/code-security.md
  --selftest  known-vulnerable snippets must be found, safe variants must not
Related: aix docs security (register state), skills security-audit-* (reasoning on the hits), security-threat-model.

Git-ignored files (2.21.43): a finding in a file that git ignores and does not track (`backend/.env` under a
`.gitignore` with `.env`) is listed as `[untracked, git-ignored]`, not gated (`--strict` gates it): nothing entered
the repository; the advice is to keep it ignored and ship a `.env.example` with placeholders. Outside a git checkout
every file counts as tracked.
