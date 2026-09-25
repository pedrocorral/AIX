# Benchmark: the kit's code tools against mature engines

Read this when: deciding whether a code tool should be replaced, wrapped or kept; before changing what a tool covers.
Skip when: running or writing tests.

Facts only. Every number below was produced by `tests/benchmark/engines.py` on 2026-09-25 (kit 2.21.19) over the twelve extended
projects (`tests/extended/projects.json`, cached clones at their pinned commits, never in the repository) and every
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

1. **Whole categories ours does not cover** (true findings, low to medium value):
   GitHub Actions: mutable action tags (`uses: actions/checkout@v4`, 100+ across ten projects) and shell injection in
   `run:` (`flask/.github/workflows/publish.yaml:49`, `ripgrep/.github/workflows/release.yml:24`); dependabot without
   cooldown; Kubernetes and compose security contexts (`spring-petclinic/k8s/db.yml:42`, `NodeGoat/docker-compose.yml:13`);
   express-session and cookie-session options, six rules on one line (`NodeGoat/server.js:78`); Spring
   `@RequestMapping` without a method (`WebGoat .../StartLesson.java:71`, 15 hits); scripts from a CDN without SRI;
   `postMessage` with `*`; prototype-pollution loops; `new RegExp(variable)`; JWT literals in code and docs.
2. **Ours missed, theirs found, in application code**: `express/examples/session/index.js:19` and three more
   `secret: 'keyboard cat'` (semgrep express-session-hardcoded-secret; our secret rule rejects a value with a space);
   `express/examples/vhost/index.js:30` `res.send('requested ' + req.params.sub)` (semgrep direct-response-write; ours
   taint does not treat `main = express()` as an app); `NodeGoat/config/env/test.js:6` `zapApiKey: "v9dn..."`
   (gitleaks generic-api-key; found by ours since 2.21.18, which carries the gitleaks rules);
   `juice-shop/lib/insecurity.ts:152` `createHmac('sha256', privateKey)` (semgrep hardcoded-hmac-key; ours flags the
   key itself at line 23, so the same root cause, one line less).
3. **Semgrep rules misapplied**: `django-no-csrf-token` on Flask, Thymeleaf and plain HTML templates (flask 8,
   spring-petclinic 3, WebGoat 75, pygoat 19+, NodeGoat 3: no Django in any of them); `non-literal-import` on
   `requests/src/requests/compat.py:24` (`importlib.import_module(lib)` over a fixed list); `direct-response-write` on
   `express/examples/route-map/index.js:37` (`escapeHtml(req.params.uid)`) and `examples/params/index.js:66` (a computed
   join); `path-join-resolve-traversal` on `juice-shop/lib/codingChallenges.ts:24` (`path.resolve` over `readdir` results).
4. **Both find** every documented vulnerability of the four vulnerable apps (table 2), and the same private keys.

### Security: what ours reports and semgrep does not

1. **Whole categories semgrep `p/default` does not cover**: unpinned dependencies and missing lockfiles, `FROM` without a
   tag, Dockerfile without `USER` (semgrep has `missing-user` but reported it only on pygoat, not NodeGoat or excalidraw),
   hard-coded credentials in data files (`juice-shop/data/static/users.yml`, 8), SQL assembled from strings then
   executed (WebGoat 5), secrets in log lines, `Math.random` for a secret, `mark_safe`/`innerHTML` on a non-literal.
2. **Ours wrong or noisy**: vendored files that our skip list does not catch, `WebGoat/src/main/resources/webgoat/static/js/libs/ace.js`
   and `jquery-*.min.js` (19 of 63 non-test findings), `juice-shop/frontend/src/assets/private/dat.gui.min.js` (15 of
   80); "path assembled from strings, opened below" on a package's own paths (`flask/src/flask/app.py:359,361,381,383`,
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
  ours "parameter `hash[]` of `toHex` is never read" on `challenge7/MD5.java:555` is false: the C-style declarator
  `byte hash[]` is misparsed (bug in ours, `hash` is read on the next line).
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
  overcounts (`?.` and `?` inside template strings), lizard undercounts (it names arrow-function class properties
  `(anonymous)` and loses their bodies). Neither is right on TSX.
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
- Ours reports dead functions for Python only; PMD `UnusedPrivateMethod` covers Java and was wrong on its one hit.

### Clones

CPD counts token windows of 60+ tokens anywhere, including inside one function and across test files; ours counts
groups of whole functions of 6+ lines with the same structure. They are not the same unit, so the numbers differ by
construction: commons-lang CPD 807 (749 test-only) vs ours 474; express CPD 139 (134 test-only) vs ours 5. Where a
group of ours is listed, CPD pairs the same files in 12 of 20 on flask, 17 of 20 on commons-lang, 0 of 20 on ripgrep
(CPD has no Rust). PMD's `ecmascript` parser does not read TypeScript: excalidraw 2 duplications, 45 with
`--language typescript`; juice-shop 109, 406 with typescript. The runner now picks the language per file extension.
Two mislabels in ours found on the way: functions in a file named `app.py` (flask's `src/flask/app.py`) are tagged
`[tests]` and not gated because `app` is an entry stem (`is_root_or_test`), and the report lists at most 20 groups
while counting all.

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
| flask | 14 / 30 | 0.8 | 16 / 0 | 4.1 | 13 / 1016 | 0.6 | 7 of 14 | 4 of 16 | 0 / 1 |
| requests | 8 / 25 | 1.0 | 6 / 0 | 3.2 | 14 / 665 | 0.4 | 4 of 8 | 3 of 6 | 0 / 0 |
| express | 5 / 24 | 1.8 | 53 / 0 | 3.0 | – | – | 0 of 5 | 0 of 53 | 0 / 0 |
| excalidraw | 12 / 0 | 5.0 | 41 / 0 | 12.9 | – | – | 1 of 12 | 1 of 41 | 0 / 0 |
| spring-petclinic | 0 / 0 | 0.3 | 16 / 0 | 3.0 | – | – | 0 of 0 | 0 of 16 | 0 / 0 |
| commons-lang | 4 / 2 | 5.2 | 8 / 0 | 6.9 | – | – | 2 of 4 | 1 of 8 | 0 / 0 |
| ripgrep | 0 / 0 | 1.3 | 16 / 0 | 3.7 | – | – | 0 of 0 | 0 of 16 | 0 / 0 |
| bat | 0 / 39 | 2.8 | 23 / 0 | 3.0 | – | – | 0 of 0 | 0 of 23 | 0 / 0 |
| NodeGoat | 16 / 0 | 0.6 | 31 / 4 | 3.7 | – | – | 8 of 16 | 7 of 31 | 0 / 0 |
| pygoat | 86 / 0 | 0.7 | 135 / 0 | 4.0 | 65 / 0 | 0.3 | 63 of 86 | 64 of 135 | 0 / 0 |
| WebGoat | 63 / 11 | 9.6 | 208 / 0 | 43.9 | – | – | 18 of 63 | 27 of 208 | 19 / 26 |
| juice-shop | 80 / 14 | 13.5 | 61 / 3 | 25.1 | – | – | 23 of 80 | 16 of 61 | 15 / 0 |

### 2. Recall on the documented vulnerabilities (tests/extended/known.json)

| project | documented vulnerabilities | ours ±1 | ours ±10 | semgrep ±1 | semgrep ±10 | bandit ±1 | bandit ±10 |
|---|---|---|---|---|---|---|---|
| NodeGoat | 6 | 6 | 6 | 6 | 6 | – | – |
| pygoat | 9 | 9 | 9 | 7 | 9 | 6 | 8 |
| WebGoat | 2 | 2 | 2 | 2 | 2 | – | – |
| juice-shop | 4 | 4 | 4 | 4 | 4 | – | – |
| total | 21 | 21 | 21 | 19 | 21 | 6 of 9 | 8 of 9 |

### 3. Rules with no counterpart on the other side (non-test findings, all projects)

semgrep-only, by rule: github-actions-mutable-action-tag 109, django-no-csrf-token 108, missing-integrity 43, detect-non-literal-regexp 25, unrestricted-request-mapping 12, detected-jwt-token 10, path-join-resolve-traversal 10, dependabot-missing-cooldown 9, direct-response-write 7, plaintext-http-link 7, express-cookie-session-default-name 6, express-cookie-session-no-domain 6, express-cookie-session-no-expires 6, express-cookie-session-no-httponly 6, express-cookie-session-no-path 6, express-cookie-session-no-secure 6, wildcard-postmessage-configuration 6, django-secure-set-cookie 5, cookie-missing-httponly 5, npm-missing-minimum-release-age 4, express-session-hardcoded-secret 4, unsafe-reflection 4, missing-user 4, formatted-sql-string 4, express-path-join-resolve-traversal 4, express-res-sendfile 4, express-check-directory-listing 4, run-shell-injection 3, unsafe-formatstring 3, prototype-pollution-loop 3, detected-bcrypt-hash 3, md5-used-as-password 3, cookie-issecure-false 3, cookie-missing-secure-flag 3, jdbc-sqli 3, template-explicit-unescape 2, using-http-server 2, run-as-non-root 2, allow-privilege-escalation-no-securitycontext 2, dangerous-globals-use 2, express-check-csurf-middleware-usage 2, secure-set-cookie 2, weak-random 2, tainted-sql-string 2, tainted-file-path 2, detect-replaceall-sanitization 2, non-literal-import 1, gha-curl-pipe-shell 1, no-sudo-in-dockerfile 1, spring-actuator-fully-enabled 1, detected-private-key 1, no-new-privileges 1, writable-filesystem-service 1, subprocess-injection 1, avoid_app_run_with_bad_host 1, missing-user-entrypoint 1, avoid-pickle 1, request-data-write 1, tainted-url-host 1, httpservlet-path-traversal 1, hardcoded-hmac-key 1, express-detect-notevil-usage 1, raw-html-format 1, express-libxml-vm-noent 1, express-open-redirect 1, express-insecure-template-usage 1, unknown-value-with-script-tag 1

bandit-only, by test id: B105 12, B101 11, B603 5, B404 4, B110 3, B605 2, B607 2, B403 2, B311 2, B324 2, B113 2, B406 2, B106 1, B104 1, B409 1

ours-only, by rule: HTML injected without escaping 47, hard-coded password / secret literal 15, path assembled from strings, opened below 14, secret pattern: generic-api-key 9, input reaches file path 7, container runs as root (no USER) 7, SQL built from strings 7, input reaches SQL statement 7, secret in a log line 6, unpinned dependency 4, input reaches redirect target 4, non-cryptographic randomness for a secret 4, OS command with a shell 3, input reaches shell command 3, unsafe deserialisation 3, private key in repository 3, command assembled from strings, run with a shell below 3, HTML assembled from strings, sent below 2, debug mode on 2, eval / dynamic Function 2, no lockfile next to package.json 2, cloud / API token literal 1, input reaches outbound request URL 1, unbounded dependency range 1, wildcard hosts 1, weak hash for passwords / tokens 1, input reaches eval 1, base image without a pinned tag 1, weak hash 1

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
| excalidraw | 117 | 0 | 89 / 4 | 0 | 1.1 | 53 | – |
| spring-petclinic | 1 | 0 | 0 / 1 | 0 | 0.1 | 0 | – |
| commons-lang | 73 | 0 | 58 / 7 | 0 | 1.9 | 44 | – |
| ripgrep | 46 | 0 | 44 / 0 | 0 | 0.4 | 43 | – |
| bat | 39 | 21 | 14 / 49 | 47 | 0.7 | 28 | – |
| NodeGoat | 2 | 0 | 7 / 0 | 7 | 0.2 | 0 | – |
| pygoat | 1 | 0 | 1 / 0 | 0 | 0.1 | 1 | 1 |
| WebGoat | 43 | 32 | 170 / 0 | 149 | 1.0 | 17 | – |
| juice-shop | 46 | 0 | 91 / 0 | 78 | 1.0 | 28 | – |

### 6. Dead functions: ours vs vulture (Python projects)

| project | ours dead functions | s | vulture unused function/method (≥ 60 %): non-test / test | s | both (same file:line) | vulture-only (non-test) | ours-only |
|---|---|---|---|---|---|---|---|
| flask | 1 | 0.6 | 9 / 245 | 0.2 | 1 | 8 | 0 |
| requests | 18 | 0.5 | 21 / 4 | 0.1 | 18 | 3 | 0 |
| pygoat | 4 | 0.3 | 12 / 0 | 0.1 | 4 | 8 | 0 |

### 7. Clones: ours vs PMD CPD

| project | ours exact clone groups | test-only groups | s | CPD duplications (60 tokens) | test-only | CPD languages | s | ours listed groups that CPD also pairs (same files) |
|---|---|---|---|---|---|---|---|---|
| flask | 26 | 5 of 20 listed | 0.3 | 10 | 4 | python | 0.5 | 12 of 20 |
| requests | 13 | 4 of 13 listed | 0.2 | 5 | 4 | python | 0.6 | 4 of 13 |
| express | 5 | 3 of 5 listed | 0.3 | 139 | 134 | ecmascript | 0.6 | 4 of 5 |
| excalidraw | 20 | 6 of 20 listed | 1.5 | 47 | 21 | ecmascript, typescript | 4.8 | 4 of 20 |
| spring-petclinic | 6 | 5 of 6 listed | 0.1 | 10 | 10 | java | 0.4 | 4 of 6 |
| commons-lang | 474 | 13 of 20 listed | 13.6 | 807 | 749 | java | 1.0 | 17 of 20 |
| ripgrep | 78 | 2 of 20 listed | 0.8 | 0 | 0 | none (Rust unsupported) | 0.0 | 0 of 20 |
| bat | 43 | 18 of 20 listed | 0.7 | 75 | 74 | ecmascript, java, python, typescript | 2.3 | 4 of 20 |
| NodeGoat | 0 | 0 of 0 listed | 0.1 | 10 | 0 | ecmascript | 0.6 | 0 of 0 |
| pygoat | 4 | 0 of 4 listed | 0.2 | 6 | 0 | ecmascript, python | 1.0 | 3 of 4 |
| WebGoat | 55 | 12 of 20 listed | 1.6 | 190 | 42 | ecmascript, java | 1.4 | 14 of 20 |
| juice-shop | 35 | 0 of 20 listed | 1.0 | 516 | 172 | ecmascript, python, typescript | 6.7 | 14 of 20 |

### 8. Secrets in git history: ours vs gitleaks

| project | ours secrets in history | s | gitleaks | s | gitleaks by rule | files flagged by both | files ours | files gitleaks |
|---|---|---|---|---|---|---|---|---|
| flask | 3 | 1.0 | 6 | 0.3 | generic-api-key 6 | 2 | 2 | 2 |
| requests | 4 | 1.0 | 4 | 0.6 | private-key 4 | 4 | 4 | 4 |
| express | 1 | 0.9 | 0 | 0.3 | – | 0 | 1 | 0 |
| excalidraw | 3 | 3.0 | 3 | 0.4 | gcp-api-key 2, generic-api-key 1 | 3 | 3 | 3 |
| spring-petclinic | 0 | 0.5 | 0 | 0.3 | – | 0 | 0 | 0 |
| commons-lang | 0 | 4.5 | 0 | 0.5 | – | 0 | 0 | 0 |
| ripgrep | 0 | 1.6 | 0 | 0.3 | – | 0 | 0 | 0 |
| bat | 0 | 3.3 | 0 | 0.4 | – | 0 | 0 | 0 |
| NodeGoat | 5 | 0.5 | 3 | 0.3 | generic-api-key 2, private-key 1 | 3 | 5 | 3 |
| pygoat | 12 | 0.9 | 10 | 0.4 | generic-api-key 8, jwt 2 | 3 | 4 | 3 |
| WebGoat | 23 | 3.7 | 24 | 0.6 | jwt 16, generic-api-key 6, private-key 2 | 14 | 16 | 14 |
| juice-shop | 98 | 5.8 | 50 | 0.8 | generic-api-key 38, jwt 11, private-key 1 | 22 | 52 | 22 |

### 9. Known CVEs: ours vs osv-scanner

| project | ours packages | manifests | transitive | vulnerable | advisories | s | osv-scanner: manifest (vulnerable packages, advisories) | osv advisories | s |
|---|---|---|---|---|---|---|---|---|---|
| flask | 20 | 1 | 8 | 4 | 27 | 1.5 | examples/celery/requirements.txt (4, 27) | 27 | 4.7 |
| requests | 15 | 1 | 14 | 0 | 0 | 0.6 | docs/requirements.txt (1, 2) | 2 | 6.9 |
| express | 0 | 0 | 0 | 0 | 0 | 0.1 | – | 0 | 0.1 |
| excalidraw | 3190 | 4 | 0 | 190 | 495 | 18.7 | dev-docs/yarn.lock (59, 149); src/packages/excalidraw/yarn.lock (47, 107); src/packages/utils/yarn.lock (19, 34); yarn.lock (65, 205) | 495 | 3.8 |
| spring-petclinic | 172 | 1 | 145 | 4 | 6 | 1.9 | pom.xml (4, 6) | 6 | 38.7 |
| commons-lang | 28 | 1 | 21 | 1 | 1 | 2.9 | – | 0 | 4.4 |
| ripgrep | 61 | 1 | 0 | 4 | 5 | 1.2 | Cargo.lock (4, 5) | 5 | 0.8 |
| bat | 247 | 3 | 40 | 17 | 157 | 2.6 | Cargo.lock (13, 23); assets/syntaxes/02_Extra/syntax_test_requirements.txt (3, 79); tests/syntax-tests/source/Requirements.txt/requirements.txt (3, 79) | 181 | 3.2 |
| NodeGoat | 1091 | 1 | 0 | 130 | 301 | 11.6 | package-lock.json (130, 301) | 301 | 3.9 |
| pygoat | 59 | 4 | 29 | 22 | 323 | 3.7 | dockerized_labs/broken_auth_lab/requirements.txt (4, 27); dockerized_labs/broken_auth_lab/requirements.txt (3, 26); dockerized_labs/insec_des_lab/requirements.txt (2, 14); dockerized_labs/insec_des_lab/requirements.txt (2, 14); dockerized_labs/sensitive_data_exposure/requirements.txt (2, 35); dockerized_labs/sensitive_data_exposure/requirements.txt (2, 18); requirements.txt (13, 237); requirements.txt (5, 163) | 534 | 10.8 |
| WebGoat | 239 | 1 | 205 | 43 | 135 | 4.4 | pom.xml (3, 39); pom.xml (38, 89) | 128 | 60.3 |
| juice-shop | 0 | 0 | 0 | 0 | 0 | 0.1 | – | 0 | 0.1 |


## Where the numbers come from

- `tests/benchmark/engines.py` copies each cached project, installs the kit into the copy, runs every tool, and writes
  `~/.cache/aix/benchmark/<project>.json` with one list of `file:line` findings per engine and the seconds each took.
  It needs `BENCH_DIR` (default `~/.cache/aix/bench`) with `venv/bin` (`pip install semgrep bandit ruff lizard vulture`),
  `bin/` (gitleaks, osv-scanner release binaries) and `pmd-bin-<version>/`; an engine that is missing is skipped and
  its column is empty.
- `tests/benchmark/report.py` prints the tables above from those files.
- The PMD Java rules were run by hand with `pmd check -R category/java/...` on the three Java projects and read
  against `aix code style --all`; their numbers are in the prose, not in the tables.
- Nothing in `tests/benchmark/` runs in `aix self-test` or the suite; it needs the engines and the network.
