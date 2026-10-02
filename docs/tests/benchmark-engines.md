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
- `tests/benchmark/javastyle.py` prints table 13: ours straight from `stylemetrics` on `src/main/java`, Checkstyle
  from `BENCH_DIR/checkstyle-all.jar` (the all-in-one jar of a GitHub release) with `tests/benchmark/style/checkstyle.xml`,
  PMD from `pmd-bin-<version>/` with `tests/benchmark/style/pmd.xml`; both configurations select the rows above at the kit's
  limits. It writes `~/.cache/aix/benchmark/style-<project>.json` and lists every mismatch for reading by hand.
- Nothing in `tests/benchmark/` runs in `aix self-test` or the suite; it needs the engines and the network.
