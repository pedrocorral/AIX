# Benchmark: the kit's code tools against mature engines

Read this when: deciding whether a code tool should be replaced, wrapped or kept; before changing what a tool covers.
Skip when: running or writing tests.

Facts only. Every number below was produced by `tests/benchmark/engines.py` on 2026-09-25 (kit 2.21.22) over the twelve extended
projects (`tests/extended/projects.json`; fifteen since 2.21.30, the OWASP Benchmark and two JHipster applications added, cached clones at their pinned commits, never in the repository) and every
hand verdict names the file and line so anyone can re-read it. Nothing here says which tool is better; it says what each
one found, what it missed, how long it took and where it was wrong.

## What was compared, and how

| Area | Ours | Theirs (version) | Same input |
|---|---|---|---|
| Security rules + taint | `aix code security`, `aix code vulnerabilities --taint` | semgrep 1.178.0 `--config p/default`; bandit 1.9.4 (Python) | project tree, `.aix/` and `node_modules/` excluded |
| Hygiene (unused imports/variables/parameters, swallowed exceptions, bugs) | `aix code style --all` line findings | ruff 0.16.9 `F401,F841,ARG001,ARG002,B006,E722,S110` (Python); PMD 7.7.0 `UnusedPrivateMethod, UnusedLocalVariable, UnusedFormalParameter, UnusedPrivateField, UnnecessaryImport, EmptyCatchBlock, CompareObjectsWithEquals` (Java) | same |
| Cyclomatic complexity > 10 | `aix code style --all` | lizard 1.24.0 CCN > 10; ruff `C901` (mccabe) | same |
| Dead functions | `aix code dead --functions` | vulture 2.16 `--min-confidence 60` (Python) | same |
| Clones | `aix code clones` exact groups | PMD CPD 7.7.0 `--minimum-tokens 60`, one run per language | same; CPD has no Rust |
| Secrets in git history | `aix code vulnerabilities --history` (last 300 commits) | gitleaks 8.30.1 `git` mode (whole history) | same clone |
| Known CVEs | `aix code vulnerabilities --cve` (OSV querybatch) | osv-scanner 2.6.0 `scan source -r` | same tree, live OSV |
| Licences | `aix code licenses` | pip-licenses, license-checker | not run: both read an installed environment, the working copies have none |

Not run, and why: ESLint, jscpd, knip, license-checker need npm (not on this machine); cargo clippy needs a build per
crate; SpotBugs needs compiled classes. semgrep Pro rules and cross-file taint are not in the free `p/default` set.

How a finding is matched: same file, line within ±1 for line rules (hygiene, dead code) and within ±10 for security,
because semgrep anchors "SQL built from a string" at the concatenation and ours at the `execute` call (pygoat
`introduction/views.py`: semgrep 158, ours 162). "Test" means a path under `tests/`, `test/`, `spec/`, `__tests__/`,
`src/test/`, or named `*_test`, `*.test.*`, `*.spec.*`, `Test*.java`; both sides are split the same way.
"Vendored" means `*.min.js`, `vendor/`, `libs/`, `jquery*`, `ace.js`, `three.js`, `dat.gui`, bat's `highlighting-speed-src`.
Times are wall seconds on one machine, one run, engines warm (rule packs downloaded before timing).

The documented vulnerabilities (`tests/extended/known.json`, 21 entries) are the lessons each vulnerable-by-design app
documents itself, verified line by line when the extended tests were written. They were selected before this benchmark
and independently of any engine, but the lines were written for our anchor; the ±10 column corrects that.

## Hand verdicts

Every disagreement class was read at the source. The file:line is the evidence; the verdict is one reader's.

### Security: what semgrep reports and ours does not

1. **Whole categories ours did not cover** (true findings, low to medium value; covered since 2.21.22, table 10):
   GitHub Actions: mutable action tags (`uses: actions/checkout@v4`, 100+ across ten projects) and shell injection in
   `run:` (`flask/.github/workflows/publish.yaml:49`, `ripgrep/.github/workflows/release.yml:24`); dependabot without
   cooldown; Kubernetes and compose security contexts (`spring-petclinic/k8s/db.yml:42`, `NodeGoat/docker-compose.yml:13`);
   express-session and cookie-session options, six rules on one line (`NodeGoat/server.js:78`); Spring
   `@RequestMapping` without a method (`WebGoat .../StartLesson.java:71`, 15 hits); scripts from a CDN without SRI;
   `postMessage` with `*`; prototype-pollution loops; `new RegExp(variable)`; JWT literals in code and docs.
2. **Ours missed, theirs found, in application code**: `express/examples/session/index.js:19` and three more
   `secret: 'keyboard cat'` (semgrep express-session-hardcoded-secret; our secret rule rejects a value with a space);
   `express/examples/vhost/index.js:30` `res.send('requested ' + req.params.sub)` (semgrep direct-response-write): ours
   had it too, but the report lists at most 20 findings per register row and the first benchmark run read the
   report; since 2.21.21 the runner reads the modules, and the tables below are from that run; `NodeGoat/config/env/test.js:6` `zapApiKey: "v9dn..."`
   (gitleaks generic-api-key; found by ours since 2.21.18, which carries the gitleaks rules);
   `juice-shop/lib/insecurity.ts:152` `createHmac('sha256', privateKey)` (semgrep hardcoded-hmac-key; ours flags the
   key itself at line 23, so the same root cause, one line less).
3. **Semgrep rules misapplied**: `django-no-csrf-token` on Flask, Thymeleaf and plain HTML templates (flask 8,
   spring-petclinic 3, WebGoat 75, pygoat 19+, NodeGoat 3: no Django in any of them); `non-literal-import` on
   `requests/src/requests/compat.py:24` (`importlib.import_module(lib)` over a fixed list); `direct-response-write` on
   `express/examples/route-map/index.js:37` (`escapeHtml(req.params.uid)`) and `examples/params/index.js:66` (a computed
   join); `path-join-resolve-traversal` on `juice-shop/lib/codingChallenges.ts:24` (`path.resolve` over `readdir` results).
4. **Both find** every documented vulnerability of the four vulnerable apps (table 2), and the same private keys.
5. **The categories, reproduced (2.21.22, table 10)**: every semgrep finding in the twenty-one rules of table 10 is
   reproduced by ours at its line, with two exceptions ours takes on purpose: `postMessage(x, "*")` in
   `WebGoat .../static/js/libs/ace.js:1740`, a vendored library ours never reads, and findings under `docs/`.
   Ours-only under the same rules, also on purpose: compose files without a `version:` key (compose v2:
   `spring-petclinic/docker-compose.yml`, `pygoat/docker-compose.yml`, `juice-shop/docker-compose.test.yml`), which
   semgrep's compose rules skip; a reusable workflow pinned to a tag (`flask/.github/workflows/publish.yaml:36`);
   Handlebars templates (`juice-shop/views/*.hbs`), which semgrep's HTML rule does not parse; and a literal secret in
   `cookieSession({...})` (`express/examples/cookie-sessions/index.js:13`), which its express-session rule does not
   read. Left out to match semgrep: `steps.*.outputs` and `needs.*.outputs` in `run:` (bat's CI has three) are set
   by the workflow's own steps.

### Security: what ours reports and semgrep does not

1. **Whole categories semgrep `p/default` does not cover**: unpinned dependencies and missing lockfiles, `FROM` without a
   tag, Dockerfile without `USER` (semgrep has `missing-user` but reported it only on pygoat, not NodeGoat or excalidraw),
   hard-coded credentials in data files (`juice-shop/data/static/users.yml`, 8), SQL assembled from strings then
   executed (WebGoat 5), secrets in log lines, `Math.random` for a secret, `mark_safe`/`innerHTML` on a non-literal.
2. **Ours wrong or noisy**: vendored files that our skip list did not catch, `WebGoat/src/main/resources/webgoat/static/js/libs/ace.js`
   and `jquery-*.min.js` (19 of 63 non-test findings), `juice-shop/frontend/src/assets/private/dat.gui.min.js` (15 of
   80): fixed in 2.21.21 (minified, bundled and well-known library files by name are no tool's input); "path assembled from strings, opened below" on a package's own paths (`flask/src/flask/app.py:359,361,381,383`,
   `blueprints.py:126,128`, `config.py:293`: 7 findings, all `os.path.join(self.root_path, ...)`); "HTML marked safe" in
   test files (flask 21, all `[test]`, listed not gated).
3. **Bandit**: 1000 of its 1029 flask findings are `B101 assert` in tests, 547 of 679 on requests; `B105` on
   `flask/src/flask/app.py:183` (`"SECRET_KEY": None`); `B605/B607` on `requests/setup.py:57` (`os.system` of a constant);
   `B110` on `flask/src/flask/config.py:163`, a `try/except/pass` with a comment saying why (ours exempts a commented pass
   by design, ruff `S110` flags it too). Of the 8 medium/high bandit findings on flask's non-test code, ours reports 4;
   the other 4 are the two above and two `B105` on a `None` value.

### Hygiene

- **ruff F401 on facades**: 59 of requests' 63 non-test findings are re-exports in `src/requests/__init__.py` and `compat.py`;
  ours exempts re-export and compat files by design, ruff wants `__all__` or `# noqa`.
- **ruff ARG001/ARG002** (171 on flask, 16 outside tests) are pytest fixtures, hooks and public API parameters; ours
  reports 1 parameter on flask (`src/flask/templating.py:101`), which ruff also reports.
- **pygoat**, application code with no facades: ruff 80, ours 59, 58 of ours confirmed by ruff and 62 of ruff's 80
  confirmed by ours; the rest are ruff's `ARG` (10) and a few `E722` bare-except lines ours anchors differently.
- **Java, PMD**: `commons-lang` PMD 42 non-test findings, 41 `CompareObjectsWithEquals`, e.g. `StringUtils.java:861`
  `if (str1 == str2) { // NOSONARLINT this intentionally uses ==`; ours reports none of them and 7 leftovers in tests,
  e.g. `LockingVisitorsTest.java:55` `startTimeMillis`, used only in a commented-out line 82 (true). `WebGoat` PMD 12
  non-test, ours 25; PMD `UnusedPrivateMethod` on `HintService.java:54` is used as `this::createHint` at line 49 (false);
  ours "parameter `hash[]` of `toHex` is never read" on `challenge7/MD5.java:555` was false: the C-style declarator
  `byte hash[]` was misparsed (`hash` is read on the next line); fixed in 2.21.21.
- Speed: ruff reports 0.0 s on every project (a Rust binary); ours takes 0.3 to 0.6 s for the whole style run.

### Cyclomatic complexity

- Python: the same functions in both on flask (11 of 11) and requests (13 of 14; ours adds `models.py:iter_content`,
  lizard adds `sessions.py:resolve_redirects`). ruff `C901` (mccabe) reports 8 and 11: mccabe does not count boolean
  operators or comprehensions, ours and lizard do.
- Rust: 43 of ours 46 and lizard's 44 are the same functions.
- Java: 44 of ours 73 and lizard's 65 on commons-lang. Lizard counts vendored JavaScript in WebGoat (149 of 170 are in
  `ace.js` and jQuery) that ours skips for style but not for security.
- TypeScript/TSX: 53 in common of ours 117 and lizard's 93 on excalidraw, and the values disagree: `renderElement`
  ours 18 / lizard 42, `restoreElement` 25 / 55, `renderEmbeddables` 29 / 11. Hand count of `renderEmbeddables`
  (`src/components/App.tsx:838`, McCabe: `if`, loops, `&&`, `||`, ternaries, `??`, no optional chaining): 14. Ours
  overcounted (`?.`, `x?: T` and `?` inside template strings; 16 after the 2.21.21 fix, the last two being JSX
  attribute ternaries the hand count folded), lizard undercounts (it names arrow-function class properties
  `(anonymous)` and loses their bodies).
- Both count test fixtures: bat's `tests/benchmarks/highlighting-speed-src/jquery.js` gives 21 of ours 39 and 41 of
  lizard's 63.

### Dead functions

- flask: vulture 254 unused functions at 60 %, 245 of them pytest tests; of the 9 in application code, 8 are Sphinx
  `setup`, Flask routes and hooks, `__getattr__`, or public API, and 1 is real: `src/flask/cli.py:697`
  `_path_is_ancestor`, defined and never referenced. Ours reports 1 (`testing.py:87 EnvironBuilder.json_dumps`, also in
  vulture) and misses `_path_is_ancestor` because `cli.py` is an entry module by convention (`ENTRY_STEMS`).
- requests: ours 18, vulture 25, the same 18; vulture's extra 7 are `setup.py:run_tests` (a `cmdclass`), `api.delete`,
  `sessions.delete` (public API) and 4 test helpers.
- pygoat: ours 4, vulture 12, the same 4; vulture's extra 8 are Django `handle` commands and Flask routes.
- Ours reported dead functions for Python only at the time of the run; since 2.21.27 it covers JS/TS, Rust and Java by
  tokens (private Java methods only, as PMD does; PMD `UnusedPrivateMethod` was wrong on its one hit, ours reports
  nothing on WebGoat or commons-lang and twelve unreferenced functions on ripgrep, each verified by name search).

### Clones

CPD counts token windows of 60+ tokens anywhere, including inside one function and across test files; ours counts
groups of whole functions of 6+ lines with the same structure. They are not the same unit, so the numbers differ by
construction: commons-lang CPD 807 (749 test-only) vs ours 474; express CPD 139 (134 test-only) vs ours 5. Where a
group of ours is listed, CPD pairs the same files in 12 of 20 on flask, 17 of 20 on commons-lang, 0 of 20 on ripgrep
(CPD has no Rust). PMD's `ecmascript` parser does not read TypeScript: excalidraw 2 duplications, 45 with
`--language typescript`; juice-shop 109, 406 with typescript. The runner now picks the language per file extension.
Two mislabels in ours found on the way: functions in a file named `app.py` (flask's `src/flask/app.py`) were tagged
`[tests]` and not gated because `app` is an entry stem (fixed in 2.21.21: tests are tests by path only), and the
report lists at most 20 groups while counting all.

### Secrets in git history

Measured twice: before and after 2.21.18, which put the gitleaks rule set inside the kit (`secretscan.py`,
`secretrules.py` generated from gitleaks v8.30.1 `config/gitleaks.toml`, MIT). The table below is the after.

- Before: same private keys on both sides; gitleaks extras were flask's documentation examples of `SECRET_KEY`
  (`docs/config.rst`, `docs/tutorial/deploy.rst`), pygoat's JWT literals in `introduction/static/js/a7.js:4` and
  commented-out CSRF tokens (`a7.js:7`), juice-shop base64 strings in `*.spec.ts`, and one real key ours missed,
  `NodeGoat/config/env/test.js:6` `zapApiKey`.
- After: on every project, every file gitleaks flags is flagged by ours (files flagged by both = files gitleaks, table 8).
  Ours reports more findings on juice-shop and WebGoat because the register's own low-entropy password rule
  (`password: 'admin123'` in `*.spec.ts`, `users.yml` rows) stays; those are tagged `[test]` where they are tests.
  The flask documentation examples are now reported too, tagged `[docs]`: listed, not gated.
- Ours extras that gitleaks does not have: `NodeGoat/app/views/tutorial/a2.html:153` `secret: "s3Cur3"` in tutorial
  prose; `express/examples/auth/index.js:50` `password: 'foobar'`.
- Time: ours walks the whole history in Python, 0.6 to 6.5 s per project here (shallow clones, one commit); gitleaks
  under 1 s everywhere.

### OWASP Benchmark (table 11, added with 2.21.30)

- Before 2.21.30 the Java taint scored sqli -1, cmdi 1, pathtraver 1, xss 5 (half the SQL cases, almost nothing
  else). Four things the Benchmark's code does that the walker did not: a variable declared outside a block and
  reassigned inside it (`String p = ""; if (c) { p = request.getHeader(x); }`) lost its taint when the block closed;
  a one-line `if (c) bar = param; else bar = "x";` was not read as an assignment, and the `else` branch cleared the
  taint the `if` branch had set; a method whose parameters carry `@RequestParam("x")` was not a method; qualified
  names (`new java.io.FileInputStream(`) did not match the sinks. Plus missing sinks and rules: `.command(` on a
  ProcessBuilder, `exec` on a Runtime variable, a response writer kept in a variable, session attributes, LDAP and
  XPath filters, `java.util.Random`, DES and ECB ciphers, `setSecure(false)`.
- After: true positive rates of 83 to 93 percent on the injection categories and 100 percent on cookies, ciphers
  and random, against semgrep's 82 to 96. False positive rates are lower than semgrep's on commands (66 vs 87),
  paths (65 vs 79), LDAP (53 vs 88) and SQL by taint (64 vs 73), higher on XPath; the Benchmark score (TPR minus
  FPR) is higher than semgrep's on cmdi, pathtraver, ldapi, equal on securecookie, hash, crypto and weakrand, lower on
  sqli, xss, xpathi and trustbound.
- Where the false positives come from, read in the cases: the Benchmark's "false" cases are flows a static tool
  must evaluate to clear, `bar = (7 * 18) + num > 200 ? "safe" : param` (arithmetic that always picks the constant),
  a value put in a map under one key and read back under another, a list where the parameter is added and a
  different index read. No tool in this document folds those; the walker is name-based by design and keeps the
  taint, which is the conservative side.
- The 40 hash cases both tools miss use an algorithm name read from a properties file (`getProperty("hashAlg1",
  "SHA512")` with the file saying MD5): invisible to a static read. The cipher cases of the same shape are caught by
  the `KeyGenerator.getInstance("DES")` line next to them, on both sides.

### Known CVEs

Measured twice: before and after 2.21.19, which put osv-scanner's approach inside the kit (`manifests.py`,
`depsdev.py`, `cvecheck.py`). Table 9 is the after.

- Before: ours read `requirements*.txt` (`==` only), `uv/poetry/pdm/Cargo.lock`, `package-lock.json`,
  `pnpm-lock.yaml`, queried exactly those versions, sent the whole lockfile to OSV in one call (HTTP 400
  `too many queries` above 1000, read as "unreachable": NodeGoat, 1091 packages) and died with a `TypeError` in its
  version sort on pygoat. osv-scanner also read `pom.xml`, `yarn.lock`, `Pipfile.lock`, `go.sum`, `Gemfile.lock`
  and resolved a `requirements.txt` or a pom transitively before querying.
- After: ours reads the same manifests plus `composer.lock`, resolves pins and Maven dependencies through deps.dev
  (the same graph osv-scanner uses), applies a pom's properties, dependencyManagement, parent-managed versions and
  exclusions, queries in batches of 1000, and reports one finding per vulnerable package and manifest.
- Same advisories on every lockfile: NodeGoat `package-lock.json` 301 and 301, excalidraw's four `yarn.lock` 495 and
  495, ripgrep `Cargo.lock` 5 and 5, bat `Cargo.lock` 23 and 23. Same on spring-petclinic's `pom.xml` (6, four
  packages, all transitive) and on flask's `examples/celery/requirements.txt` (27).
- Differences, by name: WebGoat 135 (ours) to 128: the two resolvers pick different versions for a few transitives
  of the same starters (jackson 2.15.3 on one side, thymeleaf 3.1.2 on the other). pygoat 323 to 430: osv-scanner
  lists each pin twice, as declared (`Django==4.2`, 93 advisories) and as resolved (`4.2.0`, the same 93), and picks
  older transitives (`urllib3 1.26.9`, 16 advisories, where deps.dev gives 1.26.20, 10); counted once per package
  its number is 327. bat 157 to 181: `Jinja2>=2.8.1` in a syntax-test fixture is a range, osv-scanner resolves
  ranges to their lowest version, ours reads `==` pins only. requests 0 to 2: `Sphinx==7.2.6` pulls `idna`, which
  osv-scanner resolved to 3.9.0 (2 advisories) and deps.dev to 3.20.0 (none); both are valid resolutions of the
  same pin on different days.
- commons-lang 1 to 0: osv-scanner reported no manifest at all for its `pom.xml` (parent `commons-parent:73`); ours
  resolved 28 packages through deps.dev and found `commons-lang3 3.14.0`, pulled in by a test dependency, with one
  advisory (the project's own earlier release).
- Neither side reads `package.json` ranges: express and juice-shop (no lockfile) get nothing from either.
- Time: ours 0.1 to 19 s per project after the first run (deps.dev answers are cached on disk, advisory details are
  fetched in parallel); osv-scanner 0.1 to 80 s (Maven resolution is its slow path).

## Tables

### 1. Security findings, time and overlap

| project | ours security+taint: non-test / test | s | semgrep p/default: non-test / test | s | bandit: non-test / test | s | ours also in semgrep (±10) | semgrep also in ours (±10) | in vendored files: ours / semgrep |
|---|---|---|---|---|---|---|---|---|---|
| flask | 19 / 30 | 0.8 | 16 / 0 | 3.6 | 13 / 1016 | 0.6 | 11 of 19 | 8 of 16 | 1 / 1 |
| requests | 9 / 25 | 0.7 | 6 / 0 | 2.9 | 14 / 665 | 0.5 | 5 of 9 | 4 of 6 | 0 / 0 |
| express | 27 / 24 | 1.2 | 53 / 0 | 2.9 | – | – | 22 of 27 | 46 of 53 | 0 / 0 |
| excalidraw | 49 / 0 | 5.1 | 41 / 0 | 10.1 | – | – | 38 of 49 | 38 of 41 | 0 / 0 |
| spring-petclinic | 19 / 0 | 0.3 | 16 / 0 | 2.7 | – | – | 15 of 19 | 13 of 16 | 0 / 0 |
| commons-lang | 6 / 2 | 5.1 | 8 / 0 | 5.9 | – | – | 4 of 6 | 3 of 8 | 0 / 0 |
| ripgrep | 14 / 0 | 1.1 | 16 / 0 | 3.0 | – | – | 14 of 14 | 14 of 16 | 0 / 0 |
| bat | 23 / 34 | 1.7 | 23 / 0 | 3.1 | – | – | 23 of 23 | 23 of 23 | 0 / 0 |
| NodeGoat | 25 / 0 | 0.6 | 31 / 4 | 2.7 | – | – | 13 of 25 | 17 of 31 | 0 / 0 |
| pygoat | 121 / 0 | 0.6 | 135 / 0 | 3.9 | 65 / 0 | 0.2 | 96 of 121 | 97 of 135 | 0 / 0 |
| WebGoat | 96 / 11 | 4.0 | 207 / 0 | 48.0 | – | – | 64 of 96 | 67 of 207 | 1 / 25 |
| juice-shop | 79 / 157 | 5.6 | 61 / 3 | 28.0 | – | – | 31 of 79 | 24 of 61 | 0 / 0 |

### 2. Recall on the documented vulnerabilities (tests/extended/known.json)

| project | documented vulnerabilities | ours ±1 | ours ±10 | semgrep ±1 | semgrep ±10 | bandit ±1 | bandit ±10 |
|---|---|---|---|---|---|---|---|
| NodeGoat | 6 | 6 | 6 | 6 | 6 | – | – |
| pygoat | 9 | 9 | 9 | 7 | 9 | 6 | 8 |
| WebGoat | 2 | 2 | 2 | 2 | 2 | – | – |
| juice-shop | 4 | 4 | 4 | 4 | 4 | – | – |
| total | 21 | 21 | 21 | 19 | 21 | 6 of 9 | 8 of 9 |

### 3. Rules with no counterpart on the other side (non-test findings, all projects)

semgrep-only, by rule: django-no-csrf-token 108, detect-non-literal-regexp 26, detected-jwt-token 10, path-join-resolve-traversal 10, plaintext-http-link 7, direct-response-write 5, prototype-pollution-loop 5, django-secure-set-cookie 5, cookie-missing-httponly 5, unsafe-reflection 4, missing-user 4, formatted-sql-string 4, express-path-join-resolve-traversal 4, express-res-sendfile 4, express-check-directory-listing 4, unsafe-formatstring 3, detected-bcrypt-hash 3, md5-used-as-password 3, cookie-issecure-false 3, cookie-missing-secure-flag 3, jdbc-sqli 3, missing-integrity 2, template-explicit-unescape 2, using-http-server 2, dangerous-globals-use 2, express-check-csurf-middleware-usage 2, secure-set-cookie 2, weak-random 2, tainted-sql-string 2, tainted-file-path 2, detect-replaceall-sanitization 2, non-literal-import 1, detected-private-key 1, subprocess-injection 1, avoid_app_run_with_bad_host 1, missing-user-entrypoint 1, avoid-pickle 1, request-data-write 1, tainted-url-host 1, httpservlet-path-traversal 1, hardcoded-hmac-key 1, express-detect-notevil-usage 1, raw-html-format 1, express-libxml-vm-noent 1, express-open-redirect 1, express-insecure-template-usage 1, unknown-value-with-script-tag 1

bandit-only, by test id: B105 12, B101 11, B603 5, B404 4, B110 3, B605 2, B607 2, B403 2, B311 2, B324 2, B113 2, B406 2, B106 1, B104 1, B409 1

ours-only, by rule: HTML injected without escaping 23, hard-coded password / secret literal 15, path assembled from strings, opened below 14, secret pattern: generic-api-key 9, container runs as root (no USER) 8, input reaches file path 7, SQL built from strings 7, input reaches SQL statement 7, secret in a log line 6, external script or stylesheet without integrity 6, action pinned to a mutable tag 5, unpinned dependency 4, input reaches redirect target 4, OS command with a shell 3, input reaches shell command 3, compose service without no-new-privileges 3, compose service with a writable root filesystem 3, unsafe deserialisation 3, command assembled from strings, run with a shell below 3, private key in repository 3, HTML assembled from strings, sent below 2, debug mode on 2, no lockfile next to package.json 2, cloud / API token literal 1, input reaches outbound request URL 1, unbounded dependency range 1, weak hash for passwords / tokens 1, wildcard hosts 1, input reaches eval 1, eval / dynamic Function 1, weak hash 1, base image without a pinned tag 1

### 4. Hygiene: ours vs ruff (Python projects)

| project | ours hygiene (leftover, swallowed, bug) | s (whole style run) | ruff F401,F841,ARG,B006,E722,S110: non-test / test | s | ruff by rule (non-test) | ours also in ruff (±1) | ruff non-test also in ours (±1) |
|---|---|---|---|---|---|---|---|
| flask | 3 | 0.7 | 17 / 161 | 0.0 | ARG001 8, ARG002 8, S110 1 | 1 of 3 | 1 of 17 |
| requests | 1 | 0.6 | 63 / 15 | 0.0 | F401 59, ARG001 2, ARG002 2 | 0 of 1 | 0 of 63 |
| pygoat | 59 | 0.3 | 80 / 0 | 0.0 | E722 30, F401 29, F841 7, ARG002 6, S110 4, ARG001 4 | 58 of 59 | 62 of 80 |

### 5. Cyclomatic complexity over 10: ours vs lizard

| project | ours functions with cyclomatic > 10 | of them in vendored files | lizard CCN > 10: non-test / test | of them in vendored files | lizard s | same function in both (file:name) | ruff C901 (mccabe > 10) |
|---|---|---|---|---|---|---|---|
| flask | 11 | 0 | 11 / 0 | 0 | 0.2 | 11 | 8 |
| requests | 14 | 0 | 13 / 0 | 0 | 0.1 | 13 | 11 |
| express | 3 | 0 | 4 / 0 | 0 | 0.3 | 1 | – |
| excalidraw | 98 | 0 | 89 / 4 | 0 | 1.0 | 50 | – |
| spring-petclinic | 1 | 0 | 0 / 1 | 0 | 0.1 | 0 | – |
| commons-lang | 73 | 0 | 58 / 7 | 0 | 1.9 | 44 | – |
| ripgrep | 45 | 0 | 44 / 0 | 0 | 0.4 | 42 | – |
| bat | 17 | 0 | 14 / 49 | 47 | 0.7 | 15 | – |
| NodeGoat | 2 | 0 | 7 / 0 | 7 | 0.1 | 0 | – |
| pygoat | 1 | 0 | 1 / 0 | 0 | 0.1 | 1 | 1 |
| WebGoat | 12 | 1 | 170 / 0 | 149 | 1.1 | 8 | – |
| juice-shop | 12 | 0 | 91 / 0 | 78 | 1.1 | 4 | – |

### 6. Dead functions: ours vs vulture (Python projects)

| project | ours dead functions | s | vulture unused function/method (≥ 60 %): non-test / test | s | both (same file:line) | vulture-only (non-test) | ours-only |
|---|---|---|---|---|---|---|---|
| flask | 1 | 0.7 | 9 / 245 | 0.2 | 1 | 8 | 0 |
| requests | 18 | 0.5 | 21 / 4 | 0.1 | 18 | 3 | 0 |
| pygoat | 4 | 0.3 | 12 / 0 | 0.1 | 4 | 8 | 0 |

### 7. Clones: ours vs PMD CPD

| project | ours exact clone groups | test-only groups | s | CPD duplications (60 tokens) | test-only | CPD languages | s | ours listed groups that CPD also pairs (same files) |
|---|---|---|---|---|---|---|---|---|
| flask | 26 | 2 of 20 listed | 0.3 | 10 | 4 | python | 0.5 | 12 of 20 |
| requests | 13 | 4 of 13 listed | 0.2 | 5 | 4 | python | 0.5 | 4 of 13 |
| express | 5 | 3 of 5 listed | 0.2 | 139 | 134 | ecmascript | 0.6 | 4 of 5 |
| excalidraw | 20 | 5 of 20 listed | 1.5 | 47 | 21 | ecmascript, typescript | 4.5 | 4 of 20 |
| spring-petclinic | 6 | 5 of 6 listed | 0.1 | 10 | 10 | java | 0.5 | 4 of 6 |
| commons-lang | 474 | 13 of 20 listed | 13.3 | 807 | 749 | java | 1.0 | 17 of 20 |
| ripgrep | 78 | 2 of 20 listed | 0.8 | 0 | 0 | none (Rust unsupported) | 0.0 | 0 of 20 |
| bat | 43 | 18 of 20 listed | 0.6 | 75 | 74 | ecmascript, java, python, typescript | 2.3 | 4 of 20 |
| NodeGoat | 0 | 0 of 0 listed | 0.1 | 10 | 0 | ecmascript | 0.5 | 0 of 0 |
| pygoat | 4 | 0 of 4 listed | 0.1 | 6 | 0 | ecmascript, python | 0.9 | 3 of 4 |
| WebGoat | 44 | 18 of 20 listed | 1.2 | 190 | 42 | ecmascript, java | 1.5 | 11 of 20 |
| juice-shop | 30 | 0 of 20 listed | 0.9 | 516 | 172 | ecmascript, python, typescript | 7.4 | 11 of 20 |

### 8. Secrets in git history: ours vs gitleaks

| project | ours secrets in history | s | gitleaks | s | gitleaks by rule | files flagged by both | files ours | files gitleaks |
|---|---|---|---|---|---|---|---|---|
| flask | 3 | 1.0 | 6 | 0.3 | generic-api-key 6 | 2 | 2 | 2 |
| requests | 4 | 0.8 | 4 | 0.6 | private-key 4 | 4 | 4 | 4 |
| express | 1 | 0.8 | 0 | 0.3 | – | 0 | 1 | 0 |
| excalidraw | 3 | 3.0 | 3 | 0.4 | gcp-api-key 2, generic-api-key 1 | 3 | 3 | 3 |
| spring-petclinic | 0 | 0.5 | 0 | 0.3 | – | 0 | 0 | 0 |
| commons-lang | 0 | 4.4 | 0 | 0.4 | – | 0 | 0 | 0 |
| ripgrep | 0 | 1.4 | 0 | 0.3 | – | 0 | 0 | 0 |
| bat | 0 | 3.2 | 0 | 0.5 | – | 0 | 0 | 0 |
| NodeGoat | 5 | 0.5 | 3 | 0.3 | generic-api-key 2, private-key 1 | 3 | 5 | 3 |
| pygoat | 12 | 0.8 | 10 | 0.3 | generic-api-key 8, jwt 2 | 3 | 4 | 3 |
| WebGoat | 23 | 3.5 | 24 | 0.5 | jwt 16, generic-api-key 6, private-key 2 | 14 | 16 | 14 |
| juice-shop | 98 | 5.9 | 50 | 0.7 | generic-api-key 38, jwt 11, private-key 1 | 22 | 52 | 22 |

### 9. Known CVEs: ours vs osv-scanner

| project | ours packages | manifests | transitive | vulnerable | advisories | s | osv-scanner: manifest (vulnerable packages, advisories) | osv advisories | s |
|---|---|---|---|---|---|---|---|---|---|
| flask | 20 | 1 | 8 | 4 | 27 | 0.7 | examples/celery/requirements.txt (4, 27) | 27 | 5.1 |
| requests | 15 | 1 | 14 | 0 | 0 | 0.5 | docs/requirements.txt (1, 2) | 2 | 6.6 |
| express | 0 | 0 | 0 | 0 | 0 | 0.1 | – | 0 | 0.1 |
| excalidraw | 3190 | 4 | 0 | 190 | 495 | 4.6 | dev-docs/yarn.lock (59, 149); src/packages/excalidraw/yarn.lock (47, 107); src/packages/utils/yarn.lock (19, 34); yarn.lock (65, 205) | 495 | 3.3 |
| spring-petclinic | 172 | 1 | 145 | 4 | 6 | 0.8 | pom.xml (4, 6) | 6 | 36.1 |
| commons-lang | 28 | 1 | 21 | 1 | 1 | 0.6 | – | 0 | 4.6 |
| ripgrep | 61 | 1 | 0 | 4 | 5 | 0.7 | Cargo.lock (4, 5) | 5 | 0.8 |
| bat | 247 | 3 | 40 | 17 | 157 | 1.0 | Cargo.lock (13, 23); assets/syntaxes/02_Extra/syntax_test_requirements.txt (3, 79); tests/syntax-tests/source/Requirements.txt/requirements.txt (3, 79) | 181 | 3.3 |
| NodeGoat | 1091 | 1 | 0 | 130 | 301 | 2.5 | package-lock.json (130, 301) | 301 | 3.9 |
| pygoat | 59 | 4 | 29 | 22 | 323 | 1.1 | dockerized_labs/broken_auth_lab/requirements.txt (4, 27); dockerized_labs/broken_auth_lab/requirements.txt (3, 26); dockerized_labs/insec_des_lab/requirements.txt (2, 14); dockerized_labs/insec_des_lab/requirements.txt (2, 14); dockerized_labs/sensitive_data_exposure/requirements.txt (2, 35); dockerized_labs/sensitive_data_exposure/requirements.txt (2, 18); requirements.txt (13, 237); requirements.txt (5, 163) | 534 | 34062.9 |
| WebGoat | 239 | 1 | 205 | 43 | 135 | 1.0 | pom.xml (3, 39); pom.xml (38, 89) | 128 | 51.5 |
| juice-shop | 0 | 0 | 0 | 0 | 0 | 0.2 | – | 0 | 0.1 |

### 10. Semgrep's categories reproduced by ours (2.21.22)

| semgrep rule | semgrep findings (12 projects, docs/ excluded) | reproduced by ours (±3 lines) | ours-only under the same rule |
|---|---|---|---|
| github-actions-mutable-action-tag | 113 | 113 | 1 |
| run-shell-injection | 3 | 3 | 0 |
| gha-curl-pipe-shell | 1 | 1 | 0 |
| dependabot-missing-cooldown | 9 | 9 | 0 |
| npm-missing-minimum-release-age | 4 | 4 | 0 |
| no-sudo-in-dockerfile | 1 | 1 | 0 |
| run-as-non-root | 2 | 2 | 0 |
| allow-privilege-escalation-no-securitycontext | 2 | 2 | 0 |
| no-new-privileges | 1 | 1 | 4 |
| writable-filesystem-service | 1 | 1 | 4 |
| express-cookie-session-no-httponly | 6 | 6 | 0 |
| express-cookie-session-no-secure | 6 | 6 | 0 |
| express-cookie-session-default-name | 6 | 6 | 0 |
| express-cookie-session-no-domain | 6 | 6 | 0 |
| express-cookie-session-no-path | 6 | 6 | 0 |
| express-cookie-session-no-expires | 6 | 6 | 0 |
| express-session-hardcoded-secret | 4 | 4 | 1 |
| missing-integrity | 41 | 41 | 6 |
| spring-actuator-fully-enabled | 1 | 1 | 0 |
| unrestricted-request-mapping | 15 | 15 | 0 |
| wildcard-postmessage-configuration | 6 | 6 | 0 |


### 11. OWASP Benchmark 1.2 (BenchmarkJava): the Java taint and rules against the ground truth

2,740 servlet test cases, 1,415 of them real vulnerabilities, with the Benchmark's own CSV saying which; scored the
way the Benchmark scores a tool, per category: true positive rate, false positive rate, score = TPR - FPR. "ours,
taint" is `aix code vulnerabilities --taint`, "ours, rules" is `aix code security`, "taint + rules" the union; semgrep
is `p/default` with its CWE metadata. Produced by `tests/benchmark/owasp.py --semgrep` (kit 2.21.30).

| category | cases | TP | FP | FN | TN | TPR | FPR | score (ours, taint) |
|---|---|---|---|---|---|---|---|---|
| sqli | 504 | 225 | 149 | 47 | 83 | 83% | 64% | 18 |
| cmdi | 251 | 110 | 83 | 16 | 42 | 87% | 66% | 21 |
| pathtraver | 268 | 114 | 88 | 19 | 47 | 86% | 65% | 21 |
| xss | 455 | 211 | 121 | 35 | 88 | 86% | 58% | 28 |
| ldapi | 59 | 24 | 17 | 3 | 15 | 89% | 53% | 36 |
| xpathi | 35 | 14 | 15 | 1 | 5 | 93% | 75% | 18 |
| trustbound | 126 | 33 | 13 | 50 | 30 | 40% | 30% | 10 |
| securecookie | 67 | 0 | 0 | 36 | 31 | 0% | 0% | 0 |
| hash | 236 | 0 | 0 | 129 | 107 | 0% | 0% | 0 |
| crypto | 246 | 0 | 0 | 130 | 116 | 0% | 0% | 0 |
| weakrand | 493 | 0 | 0 | 218 | 275 | 0% | 0% | 0 |

| category | cases | TP | FP | FN | TN | TPR | FPR | score (ours, rules) |
|---|---|---|---|---|---|---|---|---|
| sqli | 504 | 119 | 108 | 153 | 124 | 44% | 47% | -3 |
| cmdi | 251 | 0 | 0 | 126 | 125 | 0% | 0% | 0 |
| pathtraver | 268 | 0 | 0 | 133 | 135 | 0% | 0% | 0 |
| xss | 455 | 0 | 0 | 246 | 209 | 0% | 0% | 0 |
| ldapi | 59 | 0 | 0 | 27 | 32 | 0% | 0% | 0 |
| xpathi | 35 | 0 | 0 | 15 | 20 | 0% | 0% | 0 |
| trustbound | 126 | 0 | 0 | 83 | 43 | 0% | 0% | 0 |
| securecookie | 67 | 36 | 0 | 0 | 31 | 100% | 0% | 100 |
| hash | 236 | 89 | 0 | 40 | 107 | 69% | 0% | 69 |
| crypto | 246 | 130 | 0 | 0 | 116 | 100% | 0% | 100 |
| weakrand | 493 | 218 | 0 | 0 | 275 | 100% | 0% | 100 |

| category | cases | TP | FP | FN | TN | TPR | FPR | score (ours, taint + rules) |
|---|---|---|---|---|---|---|---|---|
| sqli | 504 | 237 | 183 | 35 | 49 | 87% | 79% | 8 |
| cmdi | 251 | 110 | 83 | 16 | 42 | 87% | 66% | 21 |
| pathtraver | 268 | 114 | 88 | 19 | 47 | 86% | 65% | 21 |
| xss | 455 | 211 | 121 | 35 | 88 | 86% | 58% | 28 |
| ldapi | 59 | 24 | 17 | 3 | 15 | 89% | 53% | 36 |
| xpathi | 35 | 14 | 15 | 1 | 5 | 93% | 75% | 18 |
| trustbound | 126 | 33 | 13 | 50 | 30 | 40% | 30% | 10 |
| securecookie | 67 | 36 | 0 | 0 | 31 | 100% | 0% | 100 |
| hash | 236 | 89 | 0 | 40 | 107 | 69% | 0% | 69 |
| crypto | 246 | 130 | 0 | 0 | 116 | 100% | 0% | 100 |
| weakrand | 493 | 218 | 0 | 0 | 275 | 100% | 0% | 100 |

| category | cases | TP | FP | FN | TN | TPR | FPR | score (semgrep) |
|---|---|---|---|---|---|---|---|---|
| sqli | 504 | 253 | 170 | 19 | 62 | 93% | 73% | 20 |
| cmdi | 251 | 117 | 109 | 9 | 16 | 93% | 87% | 6 |
| pathtraver | 268 | 120 | 106 | 13 | 29 | 90% | 79% | 12 |
| xss | 455 | 202 | 108 | 44 | 101 | 82% | 52% | 30 |
| ldapi | 59 | 26 | 28 | 1 | 4 | 96% | 88% | 9 |
| xpathi | 35 | 14 | 13 | 1 | 7 | 93% | 65% | 28 |
| trustbound | 126 | 43 | 18 | 40 | 25 | 52% | 42% | 10 |
| securecookie | 67 | 36 | 0 | 0 | 31 | 100% | 0% | 100 |
| hash | 236 | 89 | 0 | 40 | 107 | 69% | 0% | 69 |
| crypto | 246 | 130 | 0 | 0 | 116 | 100% | 0% | 100 |
| weakrand | 493 | 218 | 0 | 0 | 275 | 100% | 0% | 100 |

### 12. Spring Security misconfiguration (2.21.32): ours only, by design

Eight rule rows added for Java web applications: CSRF disabled (CWE-352), security headers disabled (CWE-693), CORS open
to every origin (CWE-942), everything permitted (CWE-285), Basic authentication without `requiresSecure()` (CWE-319), an
XML parser factory without external entities disabled in its method (CWE-611), H2 console or stack traces exposed
(CWE-489), a signing key in the code (CWE-798), a trust-all TLS manager or verifier (CWE-295).

None of semgrep's packs tried in this benchmark (p/default, p/java, p/spring, p/security-audit, p/owasp-top-ten) reports
a finding of these categories on the fifteen projects, so the reproduction criterion of table 10 has nothing to
reproduce; the check is reading every finding by hand instead. Non-test findings on the four Spring projects:

| project | findings | read |
|---|---|---|
| WebGoat | 5 | `container/WebSecurityConfig.java:86` csrf disabled, `:87` headers disabled, `webwolf/WebSecurityConfig.java:64` csrf disabled, `application-webgoat.properties:1` and `application-webwolf.properties:1` stack traces always: all five are what the line says |
| jhipster-sample-app | 1 | `config/SecurityConfiguration.java:47` csrf disabled: a stateless JWT API, the case the advice names as the one to document beside the line |
| jhipster-sample-app-gradle | 0 | session-based, CSRF token repository configured |
| spring-petclinic | 0 | — |
| BenchmarkJava (its helpers, not the test cases) | 3 | `helpers/Utils.java:421` `TrustSelfSignedStrategy`, `:425` `NoopHostnameVerifier` on the Benchmark's own HTTP client, `report/sonarqube/SonarReport.java:63` a `DocumentBuilderFactory` parsing `pom.xml` without hardening: all three are what the line says |

Test-file findings (tagged `[test]`): WebGoat's JWT lesson tests sign with literal keys (4 lines, `src/test` and
`src/it`), both JHipster `WebConfigurerTest.java:76` set `allowedOrigins("*")` in a test. WebGoat's XXE lesson
(`lessons/xxe/CommentsCache.java:98`) creates an `XMLInputFactory` and sets `ACCESS_EXTERNAL_DTD` in the same
method under a condition: not reported, as the rule is scoped to the method, and the lesson's vulnerability is the
branch, which a line rule cannot see.

### 13. Java style: ours vs Checkstyle 14.3.0 and PMD 7.7.0 (same rows, same limits)

`tests/benchmark/javastyle.py` on `src/main/java` of the four Spring projects. Only the rules that measure what
`aix code style` measures, at the kit's limits (`tests/benchmark/style/checkstyle.xml`, `pmd.xml`); the rest of the two
catalogues (formatting, naming, Javadoc, braces, import order) is out of scope. A function row matches when both sides
name the same function; a line row when both name the same line. Ours is the raw metric here, before the gate's
exemptions. PetClinic is zero on every row for all three tools.

Before the fixes of 2.21.33 (the run that found the three bugs below):

| row | project | ours | Checkstyle | both | PMD | both |
|---|---|---|---|---|---|---|
| cognitive > 15 | jhipster-sample-app | 1 | — | — | 0 | 0 |
| cognitive > 15 | WebGoat | 6 | — | — | 2 | 1 |
| parameters > 5 | jhipster-sample-app | 0 | 1 | 0 | 0 | 0 |
| parameters > 5 | jhipster-sample-app-gradle | 0 | 1 | 0 | 0 | 0 |
| parameters > 5 | WebGoat | 4 | 8 | 4 | 6 | 4 |

After the fixes (2.21.33), every row with a finding:

| row | project | ours | Checkstyle | both | PMD | both |
|---|---|---|---|---|---|---|
| lines > 60 | jhipster-sample-app-gradle | 1 | 1 | 1 | 0 | 0 |
| lines > 60 | WebGoat | 2 | 2 | 2 | 1 | 1 |
| cyclomatic > 10 | jhipster-sample-app | 1 | 1 | 1 | 1 | 1 |
| cyclomatic > 10 | jhipster-sample-app-gradle | 1 | 1 | 1 | 1 | 1 |
| cyclomatic > 10 | WebGoat | 3 | 3 | 3 | 2 | 2 |
| cognitive > 15 | WebGoat | 2 | — | — | 2 | 2 |
| nesting > 4 | WebGoat | 2 | 0 | 0 | 0 | 0 |
| parameters > 5 | jhipster-sample-app | 1 | 1 | 1 | 0 | 0 |
| parameters > 5 | jhipster-sample-app-gradle | 1 | 1 | 1 | 0 | 0 |
| parameters > 5 | WebGoat | 12 | 8 | 8 | 6 | 6 |
| file lines > 400 | WebGoat | 1 | 1 | 1 | — | — |
| unused import | jhipster-sample-app | 0 | 0 | 0 | 29 | 0 |
| unused import | jhipster-sample-app-gradle | 0 | 0 | 0 | 31 | 0 |
| unused import | WebGoat | 0 | 0 | 0 | 2 | 0 |
| unused variable / parameter / field | WebGoat | 4 | 4 | 4 | 4 | 4 |
| swallowed exception | WebGoat | 0 | 0 | 0 | 3 | 0 |
| == on a String | WebGoat | 1 | — | — | 1 | 1 |

| project | functions (ours) | files | ours s | Checkstyle s | PMD s |
|---|---|---|---|---|---|
| spring-petclinic | 88 | 30 | 0.1 | 0.7 | 1.3 |
| jhipster-sample-app | 394 | 81 | 0.2 | 1.0 | 1.7 |
| jhipster-sample-app-gradle | 400 | 79 | 0.2 | 1.0 | 1.7 |
| WebGoat | 718 | 257 | 0.4 | 1.4 | 2.2 |

Every mismatch read by hand:

**Bugs in ours, fixed in 2.21.33 (three).**

1. A parameter list that continued on the next line counted 0 parameters: `_params_of` read the head's last line
   only (`stylemetrics.py`). `BypassRestrictionsFrontendValidation.completed` has 8 parameters, `Vote.Vote`,
   `SqlInjectionLesson10a.completed`, `CrossSiteScriptingLesson5a.completed` and JHipster's
   `LiquibaseConfiguration.liquibase` 6, ours said 0 for all five. Heads of that shape in `src/main/java`: PetClinic 0,
   JHipster 14 and 15, WebGoat 73. Now the head runs from the match to the brace, and generics and annotation
   arguments are removed before counting commas.
2. A method head with an annotation between the modifier and the return type, `public @ResponseBody AttackResult
   resetVotes(`, was not a function for `FUNC_HEAD["java"]` (`clones.py`): absent from style, clones, the call graph
   and hygiene. `JWTHeaderKIDEndpoint.java` has four methods; ours found the constructor and the anonymous class's
   `resolveSigningKeyBytes` and missed `follow` and `resetVotes`. Heads of that shape: 1, 1, 1, 12; functions found
   went from 87/394/400/710 to 88/394/400/718.
3. Cognitive complexity was above Campbell's definition on three points: `try` added a nesting level (the definition
   lists `catch`, not `try`); every `&&`/`||` added 1 (the definition adds 1 per sequence of like operators); `else if`
   added 2 (the definition adds 1). `SqlInjectionLesson10b.completed`: ours 18, PMD 10, hand count by the definition
   10; now 10. The other four ours-only functions and JHipster's `jwtDecoder` were the same three points; after the
   fix ours and PMD name the same two functions over 15.

**Definition or convention differences, no change (six).**

4. PMD `UnnecessaryImport`: 62 of 62 PMD-only lines are wildcard imports (`import jakarta.persistence.*;`) whose types
   the file uses; PMD cannot resolve them without a classpath and reports them as unused.
5. PMD `EmptyCatchBlock`: 3 of 3 blocks hold a comment (`// don't care`, `// user already exists continue`, `// Do
   nothing`); ours takes a statement or a comment as intent, by design (help page), and Checkstyle agrees with ours.
6. PMD `NcssCount` counts statements, not lines: `SecurityConfiguration.filterChain` and
   `SqlInjectionLesson5b.injectableQuery` are over 60 lines as one or two chained statements. Checkstyle's
   `MethodLength` agrees with ours on all three.
7. PMD's cyclomatic counts `&&`/`||` only inside a condition, Checkstyle and ours count each operator:
   `SqlInjectionLesson10b.completed` 12 on ours and Checkstyle, 7 on PMD. Checkstyle agrees with ours on all five.
8. Nesting: ours counts every block kind, Checkstyle same-kind nesting only (`NestedIfDepth`), PMD `if` only.
   `SqlInjectionLesson8.java:85` is an `if` in an `if` in an `if` in a `try` in a try-with-resources: five block
   levels, three `if`s; `JWTHeaderKIDEndpoint.resetVotes` (found since 2.21.33) is the same shape.
9. Parameters on WebGoat, 12 on ours against 8 and 6: the four extra are `@Override` methods
   (`computeTemplateResource` three times, `beforeBodyWrite`), which Checkstyle skips by configuration
   (`ignoreOverriddenMethods`) and the kit's gate skips as decorated (framework-mapped, no limit); the raw metric
   counts them. PMD's `ExcessiveParameterList` also leaves out the two `completed` methods with 6 parameters that
   Checkstyle and ours report; its count is by its own rule, not read further.

### 14. JS/TS style: ours vs ESLint 10.12.0 (typescript-eslint parser 8.71, SonarJS plugin 4.2) on the same functions

`tests/benchmark/jsstyle.py` on the six JS/TS projects of the cache, both sides reading the same file list (the kit's
code roots, vendored files and `node_modules` left out). ESLint runs with every threshold at 0 so it reports each
function with its value (`tests/benchmark/style/eslint.config.mjs`); the runner pairs its functions with ours by file,
line and name, then applies the kit's limits to both sides. Ours is the raw metric, before the gate's exemptions.
Node and ESLint live in the benchmark folder, outside the repository.

**Which functions each side sees.** ESLint measures every function including anonymous ones; ours measures the named
units its head patterns know. The unpaired ESLint functions, by kind:

| project | files | functions ours | functions ESLint | paired | ESLint-only, by kind | ours s | ESLint s |
|---|---|---|---|---|---|---|---|
| express | 152 | 144 | 3262 | 144 | anonymous function 2977, named function 77, named method 64 | 0.2 | 1.0 |
| NodeGoat | 44 | 38 | 268 | 35 | anonymous arrow 203, anonymous function 29, named method 1 | 0.1 | 0.6 |
| juice-shop | 585 | 869 | 5015 | 829 | anonymous arrow 3619, anonymous function 399, named function 92, named method 73 | 0.9 | 2.1 |
| excalidraw | 379 | 1261 | 4723 | 1257 | anonymous arrow 2734, anonymous function 275, named method 265, named function 191 | 2.4 | 2.9 |
| jhipster-sample-app | 286 | 384 | 2205 | 378 | anonymous arrow 1400, anonymous function 316, named method 78, named arrow 24, named function 9 | 0.4 | 1.2 |
| jhipster-sample-app-gradle | 289 | 385 | 2217 | 379 | anonymous arrow 1402, anonymous function 322, named method 81, named arrow 24, named function 9 | 0.4 | 1.2 |

**The metrics on the paired functions**, and how many each side puts over the kit's limit:

| metric | project | equal | within 1 | further apart | ours over | ESLint over | both |
|---|---|---|---|---|---|---|---|
| lines > 60 | express | 144 | 0 | 0 | 3 | 3 | 3 |
| lines > 60 | NodeGoat | 35 | 0 | 0 | 8 | 8 | 8 |
| lines > 60 | juice-shop | 778 | 8 | 43 | 14 | 14 | 14 |
| lines > 60 | excalidraw | 579 | 0 | 678 | 118 | 135 | 118 |
| lines > 60 | jhipster-sample-app | 358 | 0 | 20 | 0 | 0 | 0 |
| lines > 60 | jhipster-sample-app-gradle | 357 | 0 | 22 | 0 | 0 | 0 |
| cyclomatic > 10 | express | 118 | 16 | 10 | 3 | 1 | 1 |
| cyclomatic > 10 | NodeGoat | 18 | 5 | 12 | 2 | 0 | 0 |
| cyclomatic > 10 | juice-shop | 629 | 88 | 112 | 12 | 7 | 4 |
| cyclomatic > 10 | excalidraw | 811 | 203 | 243 | 97 | 87 | 68 |
| cyclomatic > 10 | jhipster-sample-app | 316 | 40 | 22 | 2 | 1 | 1 |
| cyclomatic > 10 | jhipster-sample-app-gradle | 316 | 41 | 22 | 2 | 1 | 1 |
| cognitive > 15 | express | 110 | 10 | 24 | 2 | 1 | 1 |
| cognitive > 15 | NodeGoat | 18 | 0 | 17 | 5 | 0 | 0 |
| cognitive > 15 | juice-shop | 635 | 53 | 141 | 15 | 4 | 3 |
| cognitive > 15 | excalidraw | 775 | 211 | 271 | 84 | 54 | 50 |
| cognitive > 15 | jhipster-sample-app | 308 | 24 | 46 | 0 | 0 | 0 |
| cognitive > 15 | jhipster-sample-app-gradle | 310 | 23 | 46 | 0 | 0 | 0 |
| nesting > 4 | express | 94 | 39 | 11 | 0 | 0 | 0 |
| nesting > 4 | NodeGoat | 4 | 16 | 15 | 4 | 0 | 0 |
| nesting > 4 | juice-shop | 420 | 217 | 192 | 12 | 1 | 0 |
| nesting > 4 | excalidraw | 694 | 291 | 272 | 46 | 4 | 4 |
| nesting > 4 | jhipster-sample-app | 242 | 83 | 53 | 2 | 0 | 0 |
| nesting > 4 | jhipster-sample-app-gradle | 243 | 82 | 54 | 2 | 0 | 0 |
| parameters > 5 | express | 144 | 0 | 0 | 0 | 0 | 0 |
| parameters > 5 | NodeGoat | 35 | 0 | 0 | 1 | 1 | 1 |
| parameters > 5 | juice-shop | 797 | 19 | 13 | 17 | 17 | 17 |
| parameters > 5 | excalidraw | 1091 | 46 | 120 | 77 | 27 | 27 |
| parameters > 5 | jhipster-sample-app | 375 | 3 | 0 | 1 | 1 | 1 |
| parameters > 5 | jhipster-sample-app-gradle | 376 | 3 | 0 | 1 | 1 | 1 |

**The line rows** (file lines matched by file, the rest by line):

| row | project | ours | ESLint | both |
|---|---|---|---|---|
| file lines > 400 | express / NodeGoat / juice-shop / excalidraw / JHipster ×2 | 15 / 0 / 8 / 56 / 0 / 0 | 15 / 0 / 8 / 56 / 0 / 0 | all |
| swallowed exception | express / NodeGoat / juice-shop / excalidraw / JHipster ×2 | 0 / 0 / 1 / 3 / 0 / 0 | 0 / 0 / 1 / 3 / 0 / 0 | all |
| assignment inside a condition | express | 0 | 3 | 0 |
| unused import / variable / parameter | express | 0 | 145 | 0 |
| unused import / variable / parameter | NodeGoat | 12 | 23 | 7 |
| unused import / variable / parameter | juice-shop | 10 | 267 | 5 |
| unused import / variable / parameter | excalidraw | 34 | 371 | 1 |
| unused import / variable / parameter | jhipster-sample-app | 2 | 66 | 0 |
| unused import / variable / parameter | jhipster-sample-app-gradle | 2 | 70 | 0 |

Every mismatch read by hand:

**After the fixes of 2.21.34** (bugs 1 to 4 below), the same run:

| project | functions ours | functions ESLint | paired | ESLint-only named | ESLint-only anonymous |
|---|---|---|---|---|---|
| express | 339 (was 144) | 3262 | 339 | 14 (was 141) | 2909 |
| NodeGoat | 76 (was 38) | 268 | 73 | 0 (was 1) | 195 |
| juice-shop | 1027 (was 869) | 5015 | 975 | 54 (was 165) | 3986 |
| excalidraw | 1601 (was 1261) | 4723 | 1599 | 140 (was 456) | 2984 |
| jhipster-sample-app | 390 (was 384) | 2205 | 390 | 101 (was 111) | 1714 |

The named functions still unpaired are expression-bodied arrows with no block (`next: () => this.success.set(true)`,
33 of JHipster's first 40, 37 of juice-shop's), which are not units by the kit's definition, a head continuing on the
next line, and methods named `delete` or `default`, keywords for the head reader. Over the kit's limits on the paired
functions, ours / ESLint / both: lines express 7 / 7 / 7, excalidraw 152 / 169 / 152; cyclomatic express 9 / 3 / 3,
excalidraw 126 / 91 / 73; cognitive juice-shop 38 / 4 / 4, excalidraw 108 / 65 / 61; parameters juice-shop 18 / 17 /
17, excalidraw 81 / 27 / 27. The unused-name row: NodeGoat 7 / 23 / 7, juice-shop 22 / 267 / 19, excalidraw 17 / 371
/ 6, express and JHipster 0 on ours; the three juice-shop lines ours alone reports are two `...args` rest parameters
the body never reads (it reads `arguments`) and the known `"` inside a `'…'` string. ESLint's over-limit complexity
findings in functions ours cannot see went from 3 of 4 to 1 of 4 (express), 10 of 17 to 10 of 17 (juice-shop), 25 of
112 to 21 of 112 and 23 of 77 to 12 of 77 (excalidraw); all of those are now anonymous callbacks, the subject of the
next criterion.

**The gap closed (2.21.35).** Every JS/TS function with a block body is a unit, callbacks included, each measured on
its own code (decision 1: a nested function's branches, nesting and lines are its own, ESLint's convention;
decision 2: a function's length is the lines it owns, where ESLint counts nested bodies too). The same run:

| project | functions ours | functions ESLint | paired | unpaired ESLint functions |
|---|---|---|---|---|
| express | 3249 | 3262 | 3223 (99 %) | 25 anonymous, 14 named |
| NodeGoat | 265 | 268 | 258 (96 %) | 10 anonymous |
| juice-shop | 4451 | 5015 | 4302 (86 %) | 658 anonymous, 55 named |
| excalidraw | 3383 | 4723 | 3374 (71 %) | 1216 anonymous, 133 named |
| jhipster-sample-app | 1587 | 2205 | 1587 (72 %) | 534 anonymous, 84 named |

The unpaired functions, read from the longest down: arrows without a block (`orders.map(({ orderId }) =>`,
`beforeEach(() =>`, `PanelComponent: ({ elements }) => (`: one expression, not a unit by the kit's definition;
ESLint's over-limit findings on them are zero on every project), the `delete`/`default` methods and nested
generics fixed on the way (`addUserToCollectionIfMissing<Type extends Pick<IUser, 'id'>>(`), and one excalidraw
class field with a two-line generic default still unread. ESLint's over-limit findings in functions ours cannot
see: 0 for cyclomatic, cognitive and parameters on all six projects; 2 for lines on excalidraw. Agreement on the
paired functions, equal or within one: cyclomatic 99 % (express), 98 % (juice-shop), 91 % (excalidraw);
cognitive 99 %, 98 %, 95 %; parameters 100 %, 99 %, 95 %. Over the kit's limits, ours / ESLint / both:
cyclomatic express 5 / 4 / 4, juice-shop 14 / 17 / 11, excalidraw 109 / 112 / 89; cognitive express 3 / 3 / 3,
juice-shop 10 / 9 / 9, excalidraw 81 / 77 / 71; parameters juice-shop 20 / 17 / 17, excalidraw 97 / 27 / 27
(destructured props: decided 2026-10-04, ours counts the keys, ESLint counts one; no change). Lines is the row where decision 2 shows: ESLint puts 161 express
functions over 60 lines, ours 4, the difference being `describe` blocks that own a few lines each;
excalidraw 330 against 167. Found on the way and fixed: a `'…'` string or a regex literal holding a bracket
unbalanced the body scan (every `describe` block of the Angular spec files was lost to a `'{{ name }}'` template
string), generics after a function name were not read. Clone detection gains units too: exact groups among test
callbacks (express 9 to 214 groups, JHipster 44 to 159) are listed and, being all tests, not gated, as before.

**Bugs in ours (five), fixed in 2.21.34 except the last, which is ESLint's.**

1. Named functions ours does not see. A named function expression assigned to a property, returned or passed
   (`app.init = function init() {`, `module.exports = function query(`, `return function expressInit(`: all 23 of
   express's unpaired named functions in `lib/`), an object-literal method (`html: function () {`, `next: () =>
   this.success.set(true)`: 17 of express's first 40, 28 of juice-shop's, 30 of JHipster's), a class field holding an
   arrow (`private onUnload = () => {`: 37 of excalidraw's first 40), a getter or setter. These are absent from style,
   clones, the call graph and hygiene, and the three express assignments inside a condition (`lib/router/index.js:116`) that ESLint
   reports are inside such functions.
2. A `{` inside the head cuts the body to one line: a destructured parameter (`function handleZipFileUpload ({ file }:
   Request, …) {`, `export default function App({ appTitle, … }: AppProps) {`) or an inline object type. The function
   then measures 1 line, complexity 1, 0 parameters: 15 on juice-shop, 4 on excalidraw, 2 and 3 on JHipster, among them
   an 819-line React component. A return type with braces (`delete(series: string): Observable<{}> {`) is the same
   shape.
3. A TypeScript declaration without a body is read as a function whose body is the next block: interface and overload
   signatures (`hasAnyFilterSet(): boolean;` in `filter.model.ts`, reported with the interface's brace as its body),
   `declare global` members in the Cypress support files, `onCloseRequest: () => void` type members in excalidraw.
   4 to 12 per TypeScript project.
4. Unused-name false positives, all 34 ours-only lines on excalidraw and the 5 on NodeGoat read: a comment or an
   inline type inside a multi-line parameter list becomes a parameter name (`/* event */`, `UIAppState>["setState"];
   libraryReturnUrl`), a TypeScript parameter property (`public name: string`), a comment inside a multi-line import
   list (`// jhipster-needle-add-icon-import`), `require` lines inside an unterminated block comment read as imports
   (NodeGoat `profile-dao.js:18`, `server.js:21`), and a `"` inside a `'…'` string starting a string (juice-shop
   `customizeEasterEgg.ts:26`, `overlay` is read on the next line). The last one stays: stripping `'…'` strings
   broke on a regex literal holding an apostrophe (`/OWASP Juice Shop's/`, 23 false imports in one file), so the
   name search keeps ignoring single quotes, as JSX text needs.
5. ESLint cannot parse 35 juice-shop files (`data/static/codefixes/*.ts`, code snippets that are not standalone
   modules); ours reads them. Not a bug in ours, listed so the ours-only functions there are explained.

**Definition differences, a decision rather than a fix (four).**

6. A nested function is counted inside the enclosing function by ours; ESLint measures each function on its own.
   Ours alone puts over the cognitive limit 1 / 5 / 12 / 34 functions (express / NodeGoat / juice-shop / excalidraw),
   of which 1 / 5 / 12 / 28 hold a nested function: `lib/response.js:sendfile` ours 14 and 26 (cyclomatic, cognitive)
   against ESLint 2 and 1, NodeGoat's `SessionHandler` 23 and 55 against 1 and 0, excalidraw's `ExcalidrawWrapper`
   66 and 161 against 11 and 2. Nesting follows: ours counts every brace (callbacks, object literals), ESLint's
   `max-depth` counts control blocks only: ours alone 4 / 12 / 46 / 2 over 4.
7. Lines: ours counts the body from its brace, ESLint from the head's first line. The 611 excalidraw pairs where ours
   is shorter with the same reported line are multi-line arrow heads (`RoomModal` 150 vs 158, eight lines of
   destructured props); the 62 "head only" differences elsewhere are the same. ESLint puts 135 excalidraw functions
   over 60 lines, ours 118.
8. Parameters: a destructured object is one parameter for ESLint and its keys for ours: 129 of excalidraw's 166
   differing pairs, and 44 functions over 5 on ours alone are React components taking one props object
   (`LayerUI` ours 19, ESLint 1). Both sides agree on every plain list (17 / 17 on juice-shop, 27 / 27 on excalidraw).
9. Unused names on ESLint's side: `no-unused-vars` is ESLint's base rule, which does not understand TypeScript. Of the
   ESLint-only lines, express 131 and NodeGoat 13 are callback parameters (`req`, `res`, `next`, `err`) and 14 more
   are in test files, both exempt in ours by design; juice-shop 155 and JHipster 27 are constructor parameter
   properties (`private readonly http: HttpClient`), excalidraw 88 are interface or type members, 9 / 12 / 12 are
   enum members, the rest function-type parameter names (`(sizes: StorageSizes) => void`) and overload signatures.
   ESLint's `no-empty` and `no-cond-assign` agree with ours on every line ours reads.

### 15. Ownership on `{id}` handlers (2.21.36, VUL-AUTHZ-001): ours only, read by hand

No engine in this benchmark has a rule for object-level authorisation, so the measure is reading every finding and
every handler the rule skipped. `authz.py` on the Java projects of the cache, non-test code:

| project | handlers with a path parameter | reported | read |
|---|---|---|---|
| jhipster-sample-app (and the Gradle twin) | 17 | 4, then 8 with 2.21.37 | `BankAccountResource.java:77, 111, 165, 178`: update, patch, get and delete a `BankAccount` (`private User user`) by id, loaded with `findById`/`findOneWithEagerRelationships`, no principal read, no annotation; the repository has `findByUserIsCurrentUser` but the id handlers do not use it. Skipped: `Label` and `Authority` (no owner field), `User` (the `UserResource` handlers carry `@PreAuthorize("hasRole('ADMIN')")`), `Operation` until 2.21.37, which follows one hop: `OperationResource.java:82, 116, 176, 189` reported as "owned through its bankAccount", loaded with `findById`/`findOneWithEagerRelationships`/`deleteById`, no principal read. `Label` stays silent: its only relation is a `Set<Operation>`, a collection, and collections never carry ownership |
| WebGoat | 9 | 2 | `lessons/idor/IDORViewOtherProfile.java:57` and `IDOREditOtherProfile.java:56`: the IDOR lesson, `new UserProfile(userId)` from the path (`private String userId`), the only check a comparison against a session value the rule does not know (`userSessionData.getValue("idor-authenticated-user-id")`), and the lesson's point is that it is wrong. The other seven path-parameter handlers build nothing owned |
| spring-petclinic | 4 | 0 | no Spring Security in the build and no security configuration: nothing to own |
| BenchmarkJava, commons-lang | 0 | 0 | — |

`tests/test_authz.py` plants one handler per situation: the bare one and a service that loads by id alone are
reported; a security annotation, a `Principal` parameter with an owner comparison, a service reading the current
user, an owner-aware repository call, an entity without an owner and a project without authentication are not.

### 16. Python and Rust cognitive complexity: ours vs complexipy and rust-code-analysis (2.21.38)

Both references implement SonarSource's definition and print a value per function. Python: complexipy 8.0.1 on
flask, requests, pygoat and the kit's own scripts and tests (`tests/benchmark/pystyle.py`, paired by file and
qualified name; of several definitions with one name, typing overloads and property setters, the last one). Rust:
rust-code-analysis 0.0.25 (Mozilla) on ripgrep and bat (`tests/benchmark/ruststyle.py`, paired by file and the
line of the `fn`), with clippy's `cognitive_complexity`, `too_many_arguments` and `too_many_lines` lints as a
second column. Both toolchains live in the benchmark folder outside the repository (a rustup toolchain with clippy,
630 MB; rust-code-analysis built with `cargo install --locked`).

Before the fixes, Python: flask 784 equal / 29 within one / 23 apart of 836, requests 564 / 15 / 17, pygoat 177 /
1 / 1, the kit 1008 / 191 / 372 of 1571, ours below complexipy in 335 of the kit's 372. Rust against
rust-code-analysis: bat 406 equal / 61 / 54 of 521, ripgrep 2405 / 159 / 144 of 2708, ours above in every large
function.

After the fixes:

| project | functions | paired | equal | within 1 | further apart | ours > 15 | reference > 15 | both |
|---|---|---|---|---|---|---|---|---|
| flask | 836 | 823 | 796 | 19 | 8 | 11 | 11 | 11 |
| requests | 596 | 596 | 588 | 3 | 5 | 13 | 13 | 13 |
| pygoat | 179 | 179 | 178 | 1 | 0 | 4 | 4 | 4 |
| aix (the kit) | 1573 | 1573 | 1242 | 140 | 191 | 4 | 2 | 1 |
| bat | 521 | 521 | 473 | 37 | 11 | 10 | 9 | 9 |
| ripgrep | 2709 | 2708 | 2627 | 56 | 25 | 29 | 28 | 28 |

Every difference read by hand, with planted probes through both references where the reading needed one:

**Bugs in ours, fixed (five).**

1. Python comprehensions were not counted. A list, set, dict comprehension or generator expression is a loop: +1 and
   its nesting level, +1 per further `for`, +1 per `if` clause, and what it holds is one level deeper. The kit's own
   code is written in comprehensions, which is why 335 of its functions read lower than complexipy.
2. Python `else:` holding a single `if` was read as `elif`: the AST is the same shape, the column tells them apart.
   `Server.__exit__` in requests' test server: ours 2, by the definition 4.
3. Rust `?` was counted as a ternary (the walker's `?` is the JS/Java one): `read(p)?` on every line of a function
   added 1 each. Rust has no ternary.
4. A Rust `match` arm's block was a nesting level of its own, so an `if` inside an arm cost one more than the
   definition says (the `match` is the level).
5. A Rust match guard (`Arg::Short(ch) if ch == 'h' =>`) was a branch; it is part of the arm.

**Where the reference is short, no change (Python).** The kit's remaining 191 differences, all read by construct:
complexipy does not look into generator expressions that are arguments of a call with keyword arguments
(`dict(a=sum(x for x in xs))` is 0 for complexipy, 1 by the definition; the plain `sum(x for x in xs if x)` is 2 for
both), into f-strings (`f"{'x' if a else 'y'}"` is 0 for complexipy) or into lambdas (`lambda x: 1 if x else 0`
is 0), and it does not add a nesting level for a nested function (`def inner` holding an `if`: 1 for complexipy, 2
by the definition). Ours follows the definition on all four, so the kit, which is full of generator expressions in
`dict(...)` calls, reads higher. The eight flask and five requests differences are the same constructs plus
functions where ours is above by 2 to 4 for the same reasons (`routes_command` 23 against 19).

**Where the definitions differ, no change (Rust).** Parameters: rust-code-analysis and clippy count `self`, ours
does not (150 of bat's 521 differ by exactly one, every one a method). Lines: ours counts the body from its brace,
rust-code-analysis the span from the `fn` line, so a multi-line head or a doc comment above makes the difference
(46 on bat); over 60 lines both sides name the same 17 on bat and 38 of 39 and 42 on ripgrep. Clippy's
`too_many_lines` leaves out blank and comment lines (187 differ on bat) and its `cognitive_complexity` lint is its
own algorithm, in the nursery group: 46 of bat's functions differ from both ours and rust-code-analysis. The 25
ripgrep and 11 bat functions still apart from rust-code-analysis are large `match`/`loop` bodies with closures
(`walk.rs:next` ours 30, reference 20); every one is over 15 on both sides.

### 17. Java taint through the receiver's type, two calls deep (2.21.39)

Until 2.21.38 a tainted argument passed to `accountService.find(name)` was followed into any method called `find`
with one parameter, anywhere in the project, three at most, one call deep. Now the receiver's declared type decides
(`javatypes.py`: a field, a local, a constructor, a static class name; an interface or parent type walks every
implementation one level), the name rule is the fallback when the type cannot be read, and calls are followed two
levels deep with a stack against cycles and a memo so a callee is walked once per tainted-parameter set and depth.

**OWASP Benchmark, table 11 regenerated.** Identical to before in every taint category (sqli 225 / 149, cmdi 110 /
83, pathtraver 114 / 88, xss 211 / 121, ldapi 24 / 17, xpathi 14 / 15, trustbound 33 / 13 true / false positives):
the Benchmark's cross-file pattern, `ThingInterface thing = ThingFactory.createThing(); thing.doSomething(param)`,
was already reached by name, and now is reached by type. Time on its 2,740 files: 94 s before, 95 s after, the first
run without the memo past the 120-second limit of the extended suite.

**Spring projects, every finding read.** JHipster: 0 data-flow findings before and after (its services call JPA
repositories, no string sinks). WebGoat: 20 before, 22 after, both new ones real and reachable only through the type
and the second hop:

| finding | path |
|---|---|
| `container/users/UserService.java:52`, `jdbcTemplate.execute("CREATE SCHEMA \"" + webGoatUser.getUsername() + …)` | the registration handler's username into `userService.addUser(…)`, then `createLessonsForUser(webGoatUser)` |
| `lessons/sqlinjection/introduction/SqlInjectionLesson8.java:158`, `statement.executeUpdate(logQuery)` with `action` inside | the lesson's tainted `query` into `log(connection, query)`, a second injection in the access log |

**Planted** (`tests/test_java_types.py`): a call on a field typed `AccountService` reaches that class's `find` and
not `LabelService.find`; a field typed `ThingInterface` reaches `Thing1` and `Thing2`; a two-hop chain reaches the
repository; a receiver of unknown type (`mystery.find(q)`) falls back to the name rule and reaches `LabelService`
once.

### 18. CodeQL as the taint reference (run on 2026-10-05, nothing changed in the gate yet)

CodeQL CLI 2.27.1 with `codeql/java-queries` 1.11.11, suite `java-security-extended`, on databases built from source
(`tests/benchmark/codeql.py`; the CLI, a Maven 3.9.9, a JDK 21 for WebGoat, whose Lombok does not run on this
machine's Java 25, and the databases live in the benchmark folder outside the repository). Paired with
`aix code vulnerabilities --taint` by file, CWE family and sink line within three; only the families ours has rows for
(SQL, command, path, XSS, LDAP, XPath, redirect, XXE, deserialisation, trust boundary, SSRF, code).

| project | ours | CodeQL | both | CodeQL analyze s | every CodeQL rule that fired |
|---|---|---|---|---|---|
| WebGoat | 22 | 27 | 15 | 11.7 | sql-injection 16, path-injection 7, polynomial-redos 5, missing-jwt-signature-check 5, log-injection 4, insecure-cookie 3, sensitive-cookie-not-httponly 3, spring-disabled-csrf-protection 2, unsafe-deserialization 2, insecure-randomness 2, sensitive-log 2, xxe 1, zipslip 1, potentially-weak-cryptographic-algorithm 1 |
| jhipster-sample-app | 0 | 0 | 0 | 15.1 | log-injection 21, spring-disabled-csrf-protection 1, sensitive-log 1 |
| spring-petclinic | 0 | 0 | 0 | 14.6 | tainted-arithmetic 2 |
| BenchmarkJava | 1644 | 2762 | 1000 | 18.5 | xss 1724, stack-trace-exposure 780, sql-injection 359, weak-cryptographic-algorithm 287, … |

**OWASP Benchmark, CodeQL against the ground truth** (ours in table 11; both tools without the rules rows):

| category | CodeQL TPR | CodeQL FPR | CodeQL score | ours score |
|---|---|---|---|---|
| sqli | 100 % | 89 % | 11 | 18 |
| cmdi | 100 % | 51 % | 49 | 21 |
| pathtraver | 100 % | 49 % | 51 | 21 |
| xss | 100 % | 43 % | 57 | 28 |
| ldapi | 100 % | 41 % | 59 | 36 |
| xpathi | 100 % | 35 % | 65 | 18 |
| trustbound | 100 % | 56 % | 44 | 10 |

CodeQL misses no true case and tells apart far more of the Benchmark's false ones (its 89 % on SQL is the one place
ours scores higher); ours misses 47 / 16 / 19 / 35 / 3 / 1 / 50 true cases by category, the constant-folding traps
of table 11.

**WebGoat, every mismatch read by hand.**

CodeQL only, 12:

| what | read |
|---|---|
| `SqlInjectionLesson2.java:65`, `3:63`, `4:62`, `5:80`, SQL | `completed(@RequestParam String query)` hands the whole statement to `executeQuery(query)`. Ours requires an assembled string at an SQL sink, so a raw tainted statement, the worst case, is silent. A gap in ours |
| `JWTHeaderKIDEndpoint.java:92`, SQL | the `kid` header of a JWT taken from the request into a query; ours has no JWT-header source. A gap in ours, small |
| `CommentsCache.java:105`, XXE, from `BlindSendFileAssignment.java:87` | the request body parsed as XML two calls away; ours has the factory rule (section 12) but no XML-parsing sink for a tainted document. A gap in ours |
| `ProfileZipSlip.java:67`, path | an uploaded zip's entry names into `new File`; ours has no zip-entry source. A gap in ours, small |
| `VulnerableComponentsLesson.java:57`, deserialisation | `xstream.fromXML(payload)` on a variable; ours' sink wants `new XStream().fromXML(`. A gap in ours |
| `ProfileUploadBase.java:44`, path, from `ProfileUpload.java:38` | `fullName.replace("../", "")` on the way; ours reads `.replace(` as a sanitiser, CodeQL does not (the lesson shows the bypass). A definition difference |
| `ProfileUploadRetrieval.java:97, 99, 103`, path | the same flow ours reports at line 92, where the `File` is built; CodeQL reports where it is read, outside the three-line window. Matched by flow |

Ours only, 7:

| what | read |
|---|---|
| `FileServer.java:89, 90`, path | `new File(dir, myFile.getOriginalFilename())` from an upload; CodeQL's path rule does not take the original file name as a source. Ours right |
| `ProfileUploadRetrieval.java:92`, path | the flow above, matched |
| `SSRFTask2.java:51`, SSRF | `new URL(…)` from a parameter; the suite has no SSRF rule. Ours right |
| `MissingAccessControlUserRepository.java:40`, SQL | `jdbcTemplate.update("INSERT … VALUES(:username, …)", new MapSqlParameterSource().addValue("username", user.getUsername()))`: named parameters, the tainted value never touches the statement. Ours wrong: the assembled check looks at every argument, the statement is the first one only |
| `ProfileUploadFix.java:39`, SQL | `super.execute(file, fullName…)`: `.execute(` matched the JDBC sink on any receiver. Ours wrong |
| `EncodingAssignment.java:54`, trust boundary | a session attribute built from the request's username and a random secret; CodeQL's rule wants raw servlet input. A definition difference, ours keeps the Benchmark's reading |

**What this says.** Two false positives and three real gaps in ours on one project, all in how the SQL and
deserialisation sinks are read, plus two sources ours does not know (JWT header, zip entry). The cross-file walk of
2.21.39 holds: every CodeQL cross-file flow in these families that ours misses is missed for a sink or source reason,
not for the hop.

**After 2.21.40.** SQL sinks judged on the statement argument (raw or assembled for statement-only methods, assembled
for the parameterisable ones), `.execute(` only on a statement-like receiver, `.fromXML(` on any receiver, an XML parser
fed a tainted document as an XXE sink; and two more defects found on the way: the Java method reader did not accept an
annotation before the return type (`public @ResponseBody AttackResult completed(`), so those handlers' parameters were
never sources, and the argument splitter cut a first argument at a comma inside a string literal. The same run:

| project | ours | CodeQL | both |
|---|---|---|---|
| WebGoat | 27 (was 22) | 27 | 20 (was 15) |
| BenchmarkJava | 1657 | 2762 | 1013 |

Benchmark, ours: sqli 235 true / 152 false (was 225 / 149), score 21 (was 18); every other category unchanged. WebGoat:
the four `executeQuery(query)` lessons, `Servers.java:73` and the XXE flow are matched now; the two false positives are
gone; ours gains `JWTHeaderJKUEndpoint.java:51`, an SSRF through the JWT's `jku` header that CodeQL's suite has no rule
for. Still CodeQL only: the `kid` header into SQL (the JWT's parsed header is not a source ours follows), the zip
entry's name, and `VulnerableComponentsLesson.java:57` and `ProfileUploadBase.java:44`, where a `.replace(…)` on the
way is a sanitiser for ours and not for CodeQL. Still ours only: the upload's original file name as a path, the
session attribute, and the two SSRF flows.

### 19. Infra rules: ours vs Checkov 3.3.25 (run on 2026-10-06, nothing changed in the gate yet)

`tests/benchmark/infrastyle.py` on the fifteen projects: Checkov with its dockerfile, kubernetes, helm, github_actions
and yaml frameworks on the same files, ours the infra rows of `aix code security` (Dockerfiles, compose, Kubernetes,
workflows, `.npmrc`, dependabot). Paired by file and line within three; Kubernetes pairs rarely fall within three
lines (Checkov reports at the Deployment, ours at the container), so those were read by meaning.

| project | ours | Checkov | both | | project | ours | Checkov | both |
|---|---|---|---|---|---|---|---|---|
| flask | 2 | 3 | 0 | | NodeGoat | 9 | 3 | 1 |
| requests | 1 | 0 | 0 | | pygoat | 9 | 9 | 4 |
| express | 10 | 2 | 0 | | WebGoat | 29 | 6 | 0 |
| excalidraw | 32 | 13 | 1 | | juice-shop | 21 | 14 | 3 |
| spring-petclinic | 18 | 43 | 0 | | BenchmarkJava | 10 | 6 | 2 |
| commons-lang | 2 | 0 | 0 | | jhipster-sample-app | 10 | 1 | 0 |
| ripgrep | 14 | 0 | 0 | | jhipster-sample-app-gradle | 12 | 1 | 0 |
| bat | 24 | 5 | 1 | | | | | |

Checkov takes 3 to 6 s per project. Its checks that fired, with the projects they fire on:

| Checkov check | projects | what it checks | read |
|---|---|---|---|
| CKV2_GHA_1 | 12 | top-level `permissions` not `write-all` | fires when a workflow has no `permissions:` block at all (express `ci.yml`, 190 lines, none): the token then carries the repository's default, write on older repositories. Ours has no rule. **Real risk, every project but three** |
| CKV_DOCKER_2 | 6 | a `HEALTHCHECK` instruction | operations, not risk |
| CKV_DOCKER_3 | 5 | a `USER` is created | ours matches 4 of 5 (`container runs as root (no USER)`); the fifth is bat's syntax-test fixture |
| CKV_DOCKER_7 | 2 | base image not `latest` | matched by ours (`base image without a pinned tag`) |
| CKV2_DOCKER_17 | 1 | `chpasswd` in a Dockerfile | BenchmarkJava `VMs/Dockerfile:35`, a password set at build time. Real, one project |
| CKV_DOCKER_6 | 1 | `LABEL maintainer` instead of `MAINTAINER` | style |
| CKV_K8S_20, 23 | 1 | privilege escalation, root | spring-petclinic's two Deployments: the same two findings ours reports per container (`may run as root`, `allows privilege escalation`), 17 lines apart |
| CKV_K8S_22, 28, 29, 30, 31, 37 | 1 | read-only filesystem, `NET_RAW`, a security context at all, seccomp, capabilities | the same containers, which carry no `securityContext`; ours says so through the two rows above and has no row for the filesystem, the capabilities or seccomp. Real, one project in the cache |
| CKV_K8S_14, 43, 15 | 1 | image tag not `latest`/blank, a digest, `imagePullPolicy: Always` | `image: dsyer/petclinic` with no tag: ours has this for Dockerfiles, not for manifests. Real; the digest and the pull policy are policy |
| CKV_K8S_35, 38 | 1 | secrets as files not env, service-account token not mounted | hardening, one project |
| CKV_K8S_10 to 13, 21, 40, CKV2_K8S_6 | 1 | CPU and memory requests and limits, the default namespace, a high UID, a NetworkPolicy | operations and policy |

Ours only, 191 lines across the fifteen, by rule: action pinned to a mutable tag 128, dependabot without a cooldown
11, a password or secret literal in an infra file 17, compose without `no-new-privileges` or with a writable root 10,
privileged container 4, `.npmrc` without a minimum release age 4, workflow shell injection 3, Dockerfile without a
pinned base 3. Checkov's default set has no check for a mutable action tag, a dependabot cooldown or `.npmrc`; its
secrets framework was not run (section 8 covers secrets); its compose checks are not in a default framework.

**What this says.** On what both read, the two agree. Ours has nothing on a workflow's token permissions, the one
Checkov check that fires almost everywhere and is a real hole, and nothing on a Kubernetes container's filesystem,
capabilities, seccomp or image tag. Checkov has nothing on supply-chain pinning, which is most of what ours reports.

**After 2.21.42.** A workflow with no `permissions:` block at the top or in every job, and `write-all`; a Kubernetes
container without a read-only root filesystem, with its capabilities kept, without a seccomp profile; an image in a
manifest with no tag or `latest`; `chpasswd` in a Dockerfile. The same run: ours 249 infra findings (was 191), paired
with Checkov 49 (was 12). CKV2_GHA_1 pairs on 7 of its 12 projects; of the other 5, two are files where ours reports at
line 1 and Checkov at the one job without permissions (flask `publish.yaml`, WebGoat `release.yml`), and three are
workflows whose every job carries a scoped block with one write permission (`security-events: write`,
`pull-requests: write`), which Checkov still reports as `write-all`: ours stays silent there, by its own check's
description rightly. `chpasswd` pairs 1 of 1; the Kubernetes rows pair by meaning as before. The policy checks stay
unmatched by design.

### 20. Cloud configuration: Terraform, CloudFormation and a real Helm chart (run on 2026-10-06, nothing changed in the gate)

Section 19 said no project in the cache carries Terraform or CloudFormation. Three were cloned for this run
(`tests/benchmark/cloudinfra.py`; TerraGoat and CfnGoat are Bridgecrew's deliberately vulnerable configurations,
ingress-nginx a maintained Helm chart; outside the repository, not in `projects.json`):

| project | files | ours (infra findings) | what ours found | Checkov | Checkov s |
|---|---|---|---|---|---|
| TerraGoat | 47 `.tf` | 11 | 7 mutable action tags, 3 workflows without permissions, 1 Dockerfile without USER; nothing in a `.tf` file | 467 | 3.6 |
| CfnGoat | 4 CloudFormation templates | 10 | 5 mutable action tags, 2 workflows without permissions, 3 secret literals; nothing in a template | 68 | 4.2 |
| ingress-nginx | 1 chart, 232 YAML | 65 | 15 Dockerfiles without a pinned base, 9 without USER, 7 containers × the five Kubernetes rows (the templates read as YAML, unrendered) | 519 | 4.0 |

**Terraform and CloudFormation: ours is blind.** Not one of its findings is in a `.tf` file or a template; the rows
it has read other files of the same repositories. Checkov's 467 and 68, by family, every check name read:

| family | TerraGoat | CfnGoat | examples |
|---|---|---|---|
| logging and audit off | 89 | 6 | RDS cluster log capture, S3 access logging, Azure SQL auditing, CloudTrail |
| encryption off or without a customer key | 75 | 6 | Aurora at rest, EBS, S3 default encryption, KMS CMK |
| backup, deletion protection, versioning | 49 | 3 | RDS deletion protection, S3 versioning, backup plans |
| IAM and privilege | 46 | 13 | policies with `*` actions or resources, write without constraints, credentials exposure, permissions management |
| public exposure | 44 | 27 | S3 public ACLs and policies (four checks per bucket), public RDS, public SQL server, 0.0.0.0/0 ingress |
| network | 18 | 4 | security group rules open to the world, SSH and RDP, Lambda outside a VPC |
| secrets | 18 | 2 | passwords and keys in variables and defaults |
| other | 128 | 7 | tags, descriptions, MFA, instance metadata options, Azure threat detection e-mails |

**Helm.** Checkov renders the chart with `helm` (40 pods) and runs its Kubernetes set: 22 writable filesystems, 13
each of root, seccomp, capabilities and `NET_RAW`, plus 40 service-account tokens, 38 missing NetworkPolicies and the
limits and namespace policies. Ours reads the templates as plain YAML, `{{ }}` and all, and finds 7 containers with
the five rows of 2.21.42; the chart's values and conditionals are not rendered, so containers behind an `{{ if }}` are
not seen. The rows agree where both see a container.

**What this says.** Cloud configuration is a family ours does not read at all, and until 2.21.45 the kit said
nothing about it, not even that it looked away. Since 2.21.45 the report counts the Terraform, CloudFormation and
Helm files it meets and names the Checkov command that reads them (`cloudconfig.py`); the reader itself waits for
that line to show up on a project that matters. Two ways to close it, for the person to choose: a Terraform and
CloudFormation reader in ours for the holes rather than the policies (public exposure, IAM wildcards, encryption and
logging off, secrets in variables: about 250 of TerraGoat's 467 and 50 of CfnGoat's 68), a new family and a version
of its own; or a plain statement in the report and the help page that the kit does not read cloud configuration and
that Checkov does, with the command to run it.

### 21. Run-time guards: pydantic, beartype, typeguard on the same function (run on 2026-10-07, behind `aix code defensive`)

Python never checks an annotation at run time: `double("ab")` with `n: int` returns `"abab"`. A decorator that reads
the annotations and checks every call is the only way to make them bite. The three libraries and a stdlib
decorator (plain classes by `isinstance`, slots bound once at decoration) on `plain(f: Path, names: list[str],
depth: int) -> str`, Python 3.13, 300 000 calls each (`tests/benchmark/guards.py`, the benchmark venv):

| decorator | µs per call | `list[str]` items | value rules in the annotation | `"5"` for an `int` | own class as a type | extra packages | on disk |
|---|---|---|---|---|---|---|---|
| none | 0.06 | no | no | passes | yes | 0 | 0 |
| stdlib decorator | 0.17 | no, `list` only | if written | rejected | yes | 0 | 0 |
| beartype 0.22.9 | 0.29 | one random item per call | `Annotated[int, Is[...]]` | rejected | yes | 0 | 8.3 MB |
| typeguard 4.6.0 | 4.88 | every item | no | rejected | yes | 1 | 0.3 MB |
| pydantic 2.13.5 `validate_call` | 0.77 | every item | `Field(gt=0)`, validators | **converted to 5** | only with `arbitrary_types_allowed=True` | 4 | 9 MB |
| pydantic, `strict=True` | 0.73 | every item | same | rejected | same | 4 | 9 MB |

Releases in the twelve months to 2026-10-07: pydantic 20 (a company behind it), beartype 10 (one maintainer),
typeguard 4. Import time: pydantic 23 ms, beartype 60 ms. beartype has one thing pydantic has not, a one-line
whole-package mode (`beartype_this_package()`), and a cheaper call; both conveniences, not capabilities.

**Decision.** For a project: pydantic in strict mode. It checks everything beartype checks, carries the value rule in
the annotation, and most projects already depend on it; the two settings that make it a guard rather than a parser
are `strict=True` (else `"5"` becomes 5 and no error is raised) and `arbitrary_types_allowed=True` (else a
parameter typed with the project's own class fails at import). beartype for a project that has no pydantic and wants
nothing heavy. For the kit itself neither: no dependencies, so a decorator of its own, the stdlib row. The gate
`aix code defensive` (2.21.46) counts what a project has (models, strict ones, value rules, `validate_call`) and says
which of these it calls for; its planted shapes were checked against flask, requests, pygoat and a FastAPI project
(`return open(...)` hands the file to the caller, `-> Any` includes None, `sys.exit` ends a function).

### 22. ABAP style: ours vs abaplint 2.120.70 on abap2xlsx and abapGit (2.21.47, the fifth language)

ABAP lives in git through abapGit, one file per object (`zcl_x.clas.abap`, `.intf.abap`, `.prog.abap`,
`.testclasses.abap` for its unit tests). Two real projects joined the extended suite at their release tags: abap2xlsx
v7.16.0 (98 files, 782 units) and abapGit v1.125.0 (623 files, 4 813 units). The reference is abaplint, open source,
200 default rules, the linter both projects run in CI (both are clean against their own configuration; with every
rule on, abap2xlsx gets 15 405 findings, 2 773 of them `no_prefixes`, 1 229 `remove_descriptions`: naming and layout).
Its three metric rules were run at our limits (`tests/benchmark/abapstyle.py`, the toolchain in BENCH_DIR):

| project | units | ours over: lines 60 / cognitive 15 / cyclomatic 10 / nesting 4 / params 5 | abaplint: statements > 60 / its cyclomatic > 10 / nesting > 4 | same numbers on the methods it flags | ours s | abaplint s |
|---|---|---|---|---|---|---|
| abap2xlsx | 782 | 101 / 62 / 60 / 21 / 32 | 63 / 37 / 10 | statements 59 of 59, cyclomatic by its definition 37 of 37 | 0.7 | 1.4 |
| abapGit | 4 813 | 303 / 93 / 134 / 12 / 42 | 157 / 45 / 11 | statements 54 of 54, cyclomatic by its definition 45 of 45 | 2.1 | 3.2 |

**What was learnt on the way, each one a planted test.** A chained statement counts per item (`DATA: a, b.` is
two); a chain may sit inside a call (`obj->m( : a = 1 ), a = 2 ).`), where every item closes the head's open
parenthesis; a string template `|...{ }...|` may continue on the next line inside its braces; `*` in column 1 and
`"` to the end of the line are comments, and a period in either is not a statement end. Before the chain-in-call
rule, every statement count after the first such chain in a file was low (abap2xlsx's writer: 932 for 1 148).

**Where the definitions differ, and what ours keeps.** abaplint's cyclomatic counts IF, ELSEIF, WHILE, CASE, LOOP,
CATCH, CHECK, ASSERT, CLEANUP, ENDAT and a SELECT loop, with no base 1, no DO, no WHEN, no AND/OR, limit 20; ours is
McCabe as Checkstyle counts Java: `1 +` IF, ELSEIF, each WHEN but OTHERS, LOOP, DO, WHILE, SELECT loop, AT, CATCH,
CHECK, each AND/OR (the OR of `WHEN 'A' OR 'B'` is two labels). Ours reproduces abaplint's number exactly when asked
to, which is the proof the unit reader and the statement splitter read the same code; the gate uses McCabe. Length:
abaplint counts statements (limit 100), ours lines from the head to the END word (limit 60), as for the other four
languages. Nesting: same blocks, abaplint reports one finding per file at depth 5, ours per unit at 4. Cognitive
complexity, the metric built for readability, abaplint does not have: 62 methods of abap2xlsx and 93 of abapGit are
over 15, led by `zcl_excel_ole.bind_alv_ole2` (1 978 lines, cognitive 469, 12 parameters) and
`zcl_excel_worksheet.change_cell_style` (109 parameters). Parameters: abaplint has no rule; ours reads the
definition (IMPORTING, EXPORTING, CHANGING; RETURNING is the result; USING, CHANGING, TABLES of a FORM; the `*"`
interface block of a function module). Names are case-insensitive, so ours gives no naming advice; abapdoc `"!`
above the definition is the docstring.

**Not read yet.** Graph, dead code, clones and security: an ABAP file is a style file only (`STYLE_EXT`); the
dependency reader (class names used, interfaces, INCLUDE, function modules called) and the security rules (dynamic
WHERE and table names, EXEC SQL, `CALL 'SYSTEM'`, SUBMIT with a variable, CALL TRANSACTION without AUTHORITY-CHECK,
CLIENT SPECIFIED, GENERATE SUBROUTINE POOL) are the next steps; abaplint's `sql_escape_host_variables` (17 on
abap2xlsx with every rule on), `select_add_order_by` (4) and `check_subrc` (91) are its overlapping rows. Cognitive
complexity does not yet count the branches of a COND or SWITCH expression.

### 23. ABAP module graph, dead objects and clones on abap2xlsx and abapGit (2.21.48, step 2 of the fifth language)

No engine builds a module graph for ABAP, so the reference here is the code itself: the references by shape and how
many name an object of the project, the graph, every dead candidate read by hand, the clones
(`tests/benchmark/abapdeps.py`). A node is one abapGit object with its part files folded in; an edge is one file
naming another object (section 22's statement reader strips comments and strings first, the `CALL FUNCTION` name
is read before that).

| shape | abap2xlsx: refs / project / SAP standard | abapGit: refs / project / SAP standard |
|---|---|---|
| `zcl_x=>` static call or constant | 1 249 / 810 / 424 | 9 702 / 7 239 / 2 236 |
| `TYPE REF TO zcl_x` | 1 219 / 592 / 544 | 3 331 / 1 911 / 824 |
| `NEW zcl_x(`, `CREATE OBJECT ... TYPE zcl_x` | 4 / 2 / 0 | 289 / 254 / 3 |
| `INHERITING FROM`, `INTERFACES` | 29 / 24 / 3 | 510 / 483 / 18 |
| `RAISE EXCEPTION TYPE`, `CATCH` | 139 / 87 / 38 | 803 / 296 / 504 |
| `CALL FUNCTION 'X'`, `INCLUDE`, `SUBMIT` | 34 / 0 / 0 | 570 / 5 / 0 |

The rest name dictionary types (`zexcel_cell_row`, `tadir`), which live in XML, and SAP function modules.

| project | nodes | edges | cycles | hubs | distance A -> B | dead candidates | exact clone groups / near |
|---|---|---|---|---|---|---|---|
| abap2xlsx | 90 | 300 | 3 (one of 21 nodes) | 15 | 30 edits | 10 | 38 (23 in tests) / 173 |
| abapGit | 601 | 3 026 | 2 (one of 132 nodes) | 93 | 142 edits | 0 | 297 (97 in tests) / 3 153 |

**Edges read by hand.** Ten of `zcl_abapgit_apack_helper` and ten of `zcl_excel_converter` against the code: every one
is a real use (`zcl_abapgit_popups=>center(`, `zcl_abapgit_hash=>sha1_blob(`, `TYPE zif_abapgit_git_definitions=>ty_file`,
`zcl_abapgit_version=>check_dependant_version(`). `deps/cl_package_factory.clas.abap -> deps/if_package.intf.abap` is
right too: abapGit ships stubs of those SAP objects, so they are project files.

**Dead candidates read by hand.** abapGit's first run listed 40: 5 type pools (`deps/seoc.type.abap`), 19 object
handlers `zcl_abapgit_object_*`, 3 background classes, 13 eCATT classes reached only from the handlers, 1 injector.
All real code, none dead, four causes, each now a rule with a planted test: a type pool is referenced through any
`seoc_...` name or `TYPE-POOLS seoc`; an object whose name a string in code equals (`ls_method-class =
'ZCL_ABAPGIT_BACKGROUND_PULL'`) or whose name a string prefix built with `&&` or CONCATENATE starts
(`'ZCL_ABAPGIT_OBJECT_' && lv_type`, then `CREATE OBJECT ... TYPE (lv_class)`) is live by convention, the same rule as
a folder named by a string in Python; the strings are read in the object's part files too (the prefix sat in a
`locals_imp`); `GLOBAL FRIENDS zcl_abapgit_objects_injector` is a reference. After the four: 0. abap2xlsx's 10
stay: six `zcl_excel_converter_*` classes under `not_cloud/` form a cluster that names itself and that no program,
test or other class reaches, and `zcl_excel_writer_csv`, `_xlsm`, `_huge_file` and `zcl_excel_reader_xlsm` are the
library's public API for its users, named in no project code (the XSLT names one). Both are what the line says, a
candidate for the person to confirm, as for a Python library's public modules.

**Clones.** Units of section 22 on their statements, keywords from the ABAP list, identifiers to ID, literals to
STR/NUM; the same fingerprints and thresholds as the other languages. abapGit's 297 exact groups are mostly the
object handlers' `zif_abapgit_object~changed_by`, `~exists`, `~get_metadata` implementations, the shape abapGit
repeats on purpose per object type; the report says "merge only when they share a purpose".

**Not yet.** `--functions` (dead methods, call edges by method name) against abaplint's `unused_methods`; the
security rules and the taint walk (section 22's list). Cognitive complexity does not count COND/SWITCH branches.

### 24. ABAP `--functions`: call edges through declared types and dead methods vs abaplint `unused_methods` (2.21.49)

Nodes are the units of section 22; a call is an arc only through a known target (`tests/benchmark/abapcalls.py`).
How the receiver and static calls of the two projects split by what the reader can know about them:

| receiver | abap2xlsx | abapGit |
|---|---|---|
| typed with a SAP class or interface or a dictionary type: not a project call | 2 257 (iXML, mostly) | 1 038 |
| `zcl_x=>m(` on a project class | 404 | 3 319 |
| declared TYPE REF TO a project class, `NEW`, `CAST`, a factory's RETURNING type | 826 | 2 408 |
| declared with a project interface: every implementation | 109 | 1 124 |
| `me->`, `super->` | 234 | 123 |
| not declared anywhere the reader looks (a structure field, a chained call, an interface method's parameter typed in another file): unresolved | 89 | 2 104 |
| resolved calls | 2 059 of 2 200, 94 % | 10 683 of 13 735, 78 % |
| units, call edges | 953, 1 385 | 6 052, 10 672 |

**Dead methods.** abaplint's `unused_methods` judges private and protected methods only; ours does the same and
notes a public one nobody calls without gating it, as the API of a library (a Rust `pub fn` gets the same note):

| project | ours, private or protected (gated) | ours, public (noted) | abaplint | agreement |
|---|---|---|---|---|
| abap2xlsx | 2 | 72 | 2 | the same two: `zcl_excel_writer_2007.create_xl_drawings_vml`, `_rels` |
| abapGit | 0 | 49 | 0 | exact |

**What the first run taught, each a planted test.** Ours first listed 9 private methods on abapGit that abaplint
did not: every one was called inside a string template's embedded expression, `|<tr{ get_item_class( is_item ) }>|`,
which the statement reader of section 22 blanked with the string; the code inside a template's `{ }` is code now
(calls, conditions, names), its own strings are still strings. The name of a `CALL FUNCTION 'Z_X'` and a method
named in a string literal (`lv_name = 'PRIV_DYN'. CALL METHOD (lv_name).`) are read from the raw line for the same
reason. A bare `m( )` that no class of the inheritance chain defines is a builtin (`lines( )`, `strlen( )`) or a
constructor expression, not a call. The 72 and 49 public ones are setters and API of a library and of an injector
meant for other repositories' tests, listed with the note.

**Edges read by hand.** Ten of `zcl_excel_converter` and ten of `zcl_abapgit_apack_helper`: every one a real call
(`bind_table -> zcl_excel_worksheet.bind_table` through `TYPE REF TO zcl_excel_worksheet`,
`get_dependencies_met_status -> zcl_abapgit_version.check_dependant_version` through `zcl_abapgit_version=>`).

### 25. ABAP security rules vs abaplint `dangerous_statement` and `call_transaction_authority_check` (2.21.50)

Until 2.21.50 an `.abap` file was not a scanned text at all. abaplint's two security rules are the reference
(`tests/benchmark/abapsec.py`; the findings are read from the audit report, the screen lists 25 per row):

| project | ours, ABAP findings | abaplint | at the same line in ours | ours beyond abaplint |
|---|---|---|---|---|
| abap2xlsx | 6 | 0 | 0 | 4 file paths in a variable (`OPEN DATASET lv_filename`, `gui_upload`/`gui_download`), 1 `cl_gui_frontend_services=>execute`, 1 `CALL FUNCTION l_function` |
| abapGit | 45 | 38 | 38 of 38 | 3 `CALL FUNCTION`/`CALL TRANSACTION` named at run time, 2 file paths, 1 `CLIENT SPECIFIED`, 1 OS command |

abapGit's 45 by rule: dynamic Open SQL 29, code generated at run time 9 (INSERT/DELETE REPORT, INSERT/DELETE
TEXTPOOL), program or function named at run time 3, file path 2, cross-client 1, OS command 1. All are what abapGit
is for, a generic reader and writer of repository objects, so every line is a finding to review and none a defect
by itself; the taint walk that tells a screen field from a configuration value is the next step.

**What the first run taught, each a planted test.** Dynamic SQL also puts the table right after the verb, `INSERT
(iv_name) FROM TABLE`, `DELETE (lv) FROM TABLE`, `MODIFY (lv) FROM`, `UPDATE (lv) SET`, and the name may be a class
constant, `FROM (zcl_x=>c_tabname)`, or a field, `(<ls_table>-tobj_name)`: eleven of abaplint's 38 were those shapes.
`DELETE TEXTPOOL` joins the code-generation row. A bare program after `SUBMIT` is static, a quoted function or
transaction is static; only `SUBMIT (lv)`, `CALL FUNCTION lv` and `CALL TRANSACTION lv` are chosen at run time. The
generic secret rule, which runs on every text, read `key1 = ls_dm02l-entid` as an API key sixteen times on abapGit:
in ABAP a secret is a quoted literal, so on an `.abap` file the matched value must sit inside quotes.

**Not read yet.** The taint walk (sources: `PARAMETERS`, `SELECT-OPTIONS`, `sy-ucomm`, an RFC module's IMPORTING
parameters, `request->get_form_field(`; sinks: the rows above); HTML built in strings without `escape(`, which is
abapGit's whole UI and needs the walk to tell escaped from unescaped.

### 26. The ABAP taint walk on abap2xlsx and abapGit (2.21.51, step 3b of the fifth language)

No engine walks taint through ABAP to compare against, so the two projects are the negative controls and the planted
file of `tests/test_abaptaint.py` the positive cases (`tests/benchmark/abaptaint.py`): a `PARAMETERS` field reaching
dynamic SQL three calls away (the report's top-level code, its form, a method, a private method of the same class,
across two files), stopped by `cl_abap_dyn_prg=>check_table_name_str`, by a `CASE` on the value, or by a literal in
its place; `sy-ucomm` into `SUBMIT (lv)`; the parameter of a function module its `.fugr.xml` marks remote-enabled
into `CALL 'SYSTEM'`, while the same code in a local module is no path; a request field into `html->add( )`
without `escape( )` directly and through a string variable, and not with it.

| project | sources in the code | step-3 findings | taint paths | read by hand |
|---|---|---|---|---|
| abap2xlsx | 5 `PARAMETERS` | 6 | 0 | the demo reports' parameters reach no sink: a library |
| abapGit | 12 `PARAMETERS`, 4 `sy-ucomm`, 160 `ii_event->` reads | 41 | 1 | `zcl_abapgit_frontend_services:168`, a download path built from the package of a repository the user picked by key: the walk marks the loaded object tainted as a whole (`lo_repo = get( lv_key )`), the package name itself comes from the database; a candidate a reviewer dismisses, the same coarseness the JS and Java walks have |

**What the numbers say.** abapGit's 41 step-3 lines are what section 25 expected: table names and program names
from the repository's configuration, not from a screen; the walk confirms it for 40 of them. Its 237 HTML writes
reach no path either, and for a reason the walk cannot see: the values go into attributes of page objects and are
rendered later by other methods, more than two calls and one object away. The same holds for the JS and Java walks;
a deeper or object-carrying walk is a step of its own, for every language.

**What the first run taught, each a planted test.** A call on a fresh instance, `NEW zcl_reader( )->read( )`, was
followed by nothing (added to abapcalls too, so it is an edge of section 24 now); a bare `fetch( iv_name = lv )`
inside a class was not followed; the statement reader blanks `'SYSTEM'` to a placeholder, so the kernel-call sink
reads the raw line; a report's logic lives in its forms, so its top-level code gets one hop more and the `PERFORM`
into a form is free.

### 27. ABAP hygiene vs abaplint `unused_variables` (2.21.53)

The four hygiene findings the other languages get, on ABAP units, with abaplint's `unused_variables` as the
referee for the one it has (`tests/benchmark/abaphygiene.py`):

| project | unused variables: ours / abaplint / same line | swallowed CATCH | unused private parameters | pass-through methods |
|---|---|---|---|---|
| abap2xlsx | 61 / 333 / 33 | 13 | 0 | 7 |
| abapGit | 11 / 3 / 0 | 73 | 2 | 5 |

**The definition, and why it changed during the build.** The first version used "written and never read", the
rule of the Python and JavaScript hygiene, with the read-or-write of each mention guessed from the word before it.
It reported 200 unused variables on abapGit, whose CI keeps abaplint's count at 3: `READ TABLE x` and
`APPEND ... TO x` were read as writes, and a table filled and then handed on looked never read. The guess was wrong
too often to gate on, so the rule is abaplint's: a variable that no statement but its declaration names, the
components of a `BEGIN OF ... END OF` belonging to their structure. Under it, every "ours only" line read by hand is
real: `<ls_upd>` declared and never used in `preview_database_changes`, `lv_mode` and `lv_branch` in chained
declarations nothing names again, abap2xlsx's `lc_xml_attr_true` declared in `load_drawing_anchor` and used only in
another method with its own declaration. abaplint's 300 lines beyond ours on abap2xlsx are class-level constants
and attributes in the definition part, which is outside a unit and outside this rule, as for the other languages.

**The three abaplint has no rule for.** An empty CATCH with no comment: 13 on abap2xlsx, 73 on abapGit, the
largest hygiene finding on both; its `empty_structure` covers IF, WHEN, LOOP and ELSE, not a bare CATCH. An IMPORTING
parameter of a private or protected method never named: 2 on abapGit (`iv_version` of `authorization_check`,
`iv_package` of `get_language_version`), read by hand, both real. A method whose only statement forwards every
parameter to one call: 7 on abap2xlsx (`zcl_excel_theme`'s setters onto its elements), 5 on abapGit.

## Where the numbers come from

- `tests/benchmark/engines.py` copies each cached project, installs the kit into the copy, runs every tool, and writes
  `~/.cache/aix/benchmark/<project>.json` with one list of `file:line` findings per engine and the seconds each took.
  It needs `BENCH_DIR` (default `~/.cache/aix/bench`) with `venv/bin` (`pip install semgrep bandit ruff lizard vulture`),
  `bin/` (gitleaks, osv-scanner release binaries) and `pmd-bin-<version>/`; an engine that is missing is skipped and
  its column is empty.
- `tests/benchmark/report.py` prints tables 1 to 10 from those files; `tests/benchmark/owasp.py` prints table 11 from the
  Benchmark's CSV and the modules. Table 10 (added with 2.21.22) counts, for
  every semgrep rule ours reproduces, semgrep's findings and how many ours has within three lines; `docs/` is left
  out because ours never reads it; ours-only under a rule is what ours reports with no semgrep finding nearby
  (cookie-session secrets, which semgrep's express rule does not read).
- The PMD Java rules were run by hand with `pmd check -R category/java/...` on the three Java projects and read
  against `aix code style --all`; their numbers are in the prose, not in the tables.
- `tests/benchmark/jsstyle.py` prints section 14: ours straight from `stylemetrics` on the kit's code roots, ESLint from
  `BENCH_DIR/eslint/node_modules` (eslint, @typescript-eslint/parser, eslint-plugin-sonarjs, installed with the Node
  tarball in `BENCH_DIR/node`) with `tests/benchmark/style/eslint.config.mjs` at threshold 0, so every function comes
  back with its value and the runner applies the kit's limits to both sides. It writes
  `~/.cache/aix/benchmark/jsstyle-<project>.json` with the paired functions and every mismatch.
- `tests/benchmark/javastyle.py` prints table 13: ours straight from `stylemetrics` on `src/main/java`, Checkstyle
  from `BENCH_DIR/checkstyle-all.jar` (the all-in-one jar of a GitHub release) with `tests/benchmark/style/checkstyle.xml`,
  PMD from `pmd-bin-<version>/` with `tests/benchmark/style/pmd.xml`; both configurations select the rows above at the kit's
  limits. It writes `~/.cache/aix/benchmark/style-<project>.json` and lists every mismatch for reading by hand.
- `tests/benchmark/codeql.py` prints section 18 from CodeQL databases built beforehand (`codeql database create
  --language=java --command="./mvnw -DskipTests compile"` into `BENCH_DIR/codeql/db-<project dir>`), analysed with the
  `java-security-extended` suite into SARIF, paired with `javataint.taint` and scored on the Benchmark's CSV.
- `tests/benchmark/infrastyle.py` prints section 19: Checkov (`BENCH_DIR/venv/bin/checkov`) with its dockerfile,
  kubernetes, helm, github_actions and yaml frameworks on each prepared copy, ours from `codesecurity.scan` on the
  infra files, paired by file and line.
- `tests/benchmark/cloudinfra.py` prints section 20 on three projects cloned by hand into the extended cache
  (TerraGoat, CfnGoat, ingress-nginx), Checkov's terraform, cloudformation, helm and kubernetes frameworks with
  `helm` from `BENCH_DIR/helm-bin`.
- Nothing in `tests/benchmark/` runs in `aix self-test` or the suite; it needs the engines and the network.
