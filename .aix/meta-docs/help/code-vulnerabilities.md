aix code vulnerabilities [PATH...] [--taint] [--cve] [--history] [--commits N] [--strict] [--gate] [--audit] [--report] [--selftest]

THE DEEP SECURITY LAYER, below `aix code security` (patterns) and above `aix docs security` (the register).
Three analyses, all on by default, each selectable:

  --taint     Python, through the parser, one file at a time. Sources: parameters of decorated functions (route
              handlers, commands; FastAPI Depends() excluded), request.args/form/json/headers/cookies/..., sys.argv,
              os.environ, input(), stdin. Taint follows assignments, f-strings, concatenation, loops and calls into
              functions defined in the same file (one level). Sinks: subprocess with shell=True, os.system,
              eval/exec, execute()/raw() without parameters, open/send_file/os.remove/shutil/Path, redirect,
              render_template_string/Template, yaml.load/pickle/marshal, requests/httpx/urlopen (SSRF).
              Sanitisers clear it: int/float/bool/len, shlex.quote, html/markupsafe escape, bleach.clean,
              secure_filename, uuid.UUID, re.fullmatch, a Path.resolve() in a function that checks is_relative_to.
              Output: "input reaches <sink>" with the chain (which variable, assigned where, from which source).
              Limits: Python only; a value crossing files is not followed; a taint path is static evidence that
              input CAN reach a sink, not proof of exploitability in production.
  --cve       pinned dependencies from requirements*.txt (==), uv.lock / poetry.lock / pdm.lock, package-lock.json,
              pnpm-lock.yaml, Cargo.lock, sent in one batch to the OSV database (api.osv.dev). Reports the advisory
              id, summary and the first fixed version, per VUL-DEP-001. Needs the network; when unreachable it says
              so, skips, and the gate is not failed by it.
  --history   `git log -p --all` over the last --commits N (default 300) through the secret rules of aix code
              security (private keys, cloud/API tokens, hard-coded passwords). A leaked secret in history is live
              until rotated, even if the file was cleaned. Files carrying `aix: skip-security-scan` are skipped at
              the commit where they carried it.

Every finding names the VUL row and the CWE. Test code is listed, not gated (--strict gates it). A taint sink reviewed
and accepted carries `# aix: accepted VUL-… <why>` on its line, as for aix code security: listed with the reason, never gated.
--audit writes docs/security/audits/AUDIT-<date>-vulnerabilities.md with the evidence table filled: the input
`aix docs security` needs before a status changes. --gate fails on any finding to review.
What this still is not: an authorisation or business-logic review (the security-audit-* skills), a runtime test,
or a scan of the deployed environment.
