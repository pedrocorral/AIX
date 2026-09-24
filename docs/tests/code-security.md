# Code security (generated — do not edit)

```
Code security — .aix/scripts, tests

  findings to review 0; in tests (not gated, --strict to gate) 8; register rows with rules 16, with findings 3
  A match is a finding to review, not proof of exploitability; a clean row is not proof of absence.

  VUL-INJ-002  (not in register)  [register: ?]
    tests/test_js_taint.py:67  eval / exec of dynamic code (CWE-95)  [test]
      eval(req.query.code);                                         // FIND:CWE-95
      -> no eval/exec on data; use ast.literal_eval for literals, a dispatch table for names
    tests/test_js_taint.py:76  eval / exec of dynamic code (CWE-95)  [test]
      exec(target);                                                 // FIND:CWE-78 (reached through the call below)
      -> no eval/exec on data; use ast.literal_eval for literals, a dispatch table for names
    tests/test_js_taint.py:85  eval / exec of dynamic code (CWE-95)  [test]
      exec(local);                                                  // SAFE: constant
      -> no eval/exec on data; use ast.literal_eval for literals, a dispatch table for names
    tests/test_js_taint.py:87  eval / exec of dynamic code (CWE-95)  [test]
      exec(cmd);                                                    // SAFE: cmd is a new, clean variable in this sc
      -> no eval/exec on data; use ast.literal_eval for literals, a dispatch table for names

  VUL-INJ-001  Paths from config (`code_roots`, sources) used in file operations with  [register: expected]
    tests/fixtures/java-app/src/main/java/com/acme/app/Repo.java:6  SQL built from strings, executed below (CWE-89)  [test]
      String q = "SELECT * FROM t WHERE id = " + id;  ...  return DriverManager.getConnection("jdbc
      -> PreparedStatement / parameters with ? placeholders; never concatenate values into the statement
    tests/test_js_taint.py:46  SQL built from strings, executed below (CWE-89)  [test]
      const sql = "SELECT * FROM users WHERE id = " + id;  ...  await db.query(sql);                    
      -> PreparedStatement / parameters with ? placeholders; never concatenate values into the statement
    tests/test_js_taint.py:181  SQL built from strings (CWE-89)  [test]
      await knex.raw("select " + id);                                // FIND:CWE-89
      -> parameterise: cursor.execute(sql, params); never interpolate values into SQL

  VUL-WEB-003  (not in register)  [register: ?]
    tests/test_js_taint.py:56  open redirect from input (CWE-601)  [test]
      res.redirect(req.query.next);                                 // FIND:CWE-601
      -> allow-list redirect targets or use relative paths only

  skipped by marker: .aix/scripts/securityrules.py  (aix: skip-security-scan ` in a file's head.""")
  skipped by marker: .aix/scripts/vulnerabilities.py  (aix: skip-security-scan this file describes sources and sinks and holds the self-test snippets""")
  skipped by marker: .aix/scripts/codesecurity.py  (aix: skip-security-scan this file holds the rule patterns and the known-bad self-test snippets""")
  no pattern matched for: VUL-AI-001, VUL-AI-002, VUL-AUTHN-001, VUL-AUTHN-002, VUL-DEP-001, VUL-INFRA-001, VUL-INPUT-001, VUL-INPUT-002, VUL-LOG-001, VUL-SECRET-001, VUL-SECRET-002, VUL-WEB-001, VUL-WEB-002  (rules ran; absence of a match is not evidence of absence)
  next: review each REVIEW line; fix or mark `# aix: accepted VUL-… <why>`; `aix code security --audit` writes the audit report;
        then `aix docs security` / the security-audit-* skills move register rows on that evidence.
```
