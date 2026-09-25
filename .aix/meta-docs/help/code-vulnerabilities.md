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
  --cve       Known vulnerabilities of what the project installs, from OSV (osv.dev), one finding per vulnerable
              package and manifest (a package in two lockfiles is two findings: each lockfile is fixed on its own),
              with the advisory ids, a summary and the first fixed version, per VUL-DEP-001. What is queried:
              - lockfiles as they are, they hold the whole tree: uv.lock, poetry.lock, pdm.lock, Cargo.lock,
                package-lock.json, pnpm-lock.yaml, yarn.lock (v1 and berry), Pipfile.lock, Gemfile.lock,
                composer.lock, go.sum;
              - `==` pins in any *requirements*.txt and the dependencies of every pom.xml (properties,
                dependencyManagement, versions inherited from the parent, exclusions), each resolved to the packages
                it pulls in through deps.dev (Google's open dependency graph, no key), the way osv-scanner does it;
                answers are cached under ~/.cache/aix/depsdev, a resolved version never changes.
              Not read: version ranges (`>=`, `^`) in requirements or package.json, a pom whose parent is not on
              Maven Central (its unversioned dependencies are listed as unresolved). The note under the section says
              how many packages from how many manifests, how many of them transitive, and what was unreachable:
              when OSV or deps.dev is not there it says so, skips, and the gate is not failed by it.
  --history   `git log -p --all` over every commit (or the last --commits N) through the secret rules of aix code
              security: the register's own (private keys, cloud/API tokens, hard-coded passwords) and the gitleaks
              rule set (221 provider patterns and a generic one with an entropy floor and allowlists, from
              config/gitleaks.toml, MIT). A leaked secret in history is live until rotated, even if the file was
              cleaned. Files carrying `aix: skip-security-scan` are skipped at the commit where they carried it;
              images, fonts, binaries and package-manager lockfiles are never read. A finding in documentation
              (docs/, *.md, *.rst, *.adoc) is tagged [docs]: listed, not gated, like [test].

JavaScript/TypeScript (.js .jsx .ts .tsx .mjs) is followed without a parser, statement by statement, scoped by braces:
  sources     req/request.query|params|body|headers|cookies (Express, Fastify), ctx.query|request.body (Koa),
              request.nextUrl / searchParams.get (Next), await request.json()|formData(), process.env|argv,
              location.*, new URLSearchParams, formData.get, document.cookie|referrer; destructuring counts
  carries     assignment, template literals, `+`, await, a method call on a tainted value (.trim())
  cleans      Number, parseInt, parseFloat, Boolean, encodeURIComponent, path.basename, validator.escape,
              DOMPurify.sanitize, shell-quote's quote
  sinks       exec/execSync, spawn with shell: true (CWE-78); eval, new Function, setTimeout(string) (CWE-95);
              fs.*, readFile.., res.sendFile (CWE-22); .query/.raw/.execute/$queryRawUnsafe with a template
              literal or `+` (CWE-89; a parameter array is not a finding); res.redirect, redirect, location.href =,
              window.open (CWE-601); innerHTML =, insertAdjacentHTML, document.write, dangerouslySetInnerHTML,
              res.send of assembled HTML (CWE-79); fetch, axios, http.get with an input URL (CWE-918)
  What it is not: no types, no middleware (a validator in a middleware is invisible: the finding stays), no cross-file.

Every finding names the VUL row and the CWE. Test code is listed, not gated (--strict gates it). A taint sink reviewed
and accepted carries `# aix: accepted VUL-… <why>` on its line, as for aix code security: listed with the reason, never gated.
--audit writes docs/security/audits/AUDIT-<date>-vulnerabilities.md with the evidence table filled: the input
`aix docs security` needs before a status changes. --gate fails on any finding to review.
What this still is not: an authorisation or business-logic review (the security-audit-* skills), a runtime test,
or a scan of the deployed environment.
