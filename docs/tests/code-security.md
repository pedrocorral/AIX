# Code security (generated — do not edit)

```
Code security — .aix/scripts, tests

  findings to review 0; in tests (not gated, --strict to gate) 38; accepted in code 3; register rows with rules 16, with findings 5
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
    tests/test_two_line.py:15  OS command with a shell (CWE-78)  [test]
      os.system(cmd)                                          # FIND:CWE-78
      -> subprocess.run([...], shell=False) with an argument list; validate each argument
    tests/test_two_line.py:15  command assembled from strings, run with a shell below (CWE-78)  [test]
      cmd = "ls " + name  ...  os.system(cmd)                          
      -> argument list without a shell; validate each argument
    tests/test_two_line.py:17  OS command with a shell (CWE-78)  [test]
      subprocess.run(cmd2, shell=True)                        # FIND:CWE-78
      -> subprocess.run([...], shell=False) with an argument list; validate each argument
    tests/test_two_line.py:17  command assembled from strings, run with a shell below (CWE-78)  [test]
      cmd2 = f"ls {name}"  ...  subprocess.run(cmd2, shell=True)        
      -> argument list without a shell; validate each argument
    tests/test_two_line.py:19  OS command with a shell (CWE-78)  [test]
      subprocess.run(cmd3, shell=True)                        # FIND:CWE-78
      -> subprocess.run([...], shell=False) with an argument list; validate each argument
    tests/test_two_line.py:19  command assembled from strings, run with a shell below (CWE-78)  [test]
      cmd3 = "ls {}".format(name)  ...  subprocess.run(cmd3, shell=True)        
      -> argument list without a shell; validate each argument
    tests/test_two_line.py:21  OS command with a shell (CWE-78)  [test]
      subprocess.check_output(cmd4, shell=True)               # FIND:CWE-78
      -> subprocess.run([...], shell=False) with an argument list; validate each argument
    tests/test_two_line.py:21  command assembled from strings, run with a shell below (CWE-78)  [test]
      cmd4 = "ls %s" % name  ...  subprocess.check_output(cmd4, shell=True
      -> argument list without a shell; validate each argument
    tests/test_two_line.py:27  OS command with a shell (CWE-78)  [test]
      os.system(cmd6)                                         # SAFE: reassigned in between
      -> subprocess.run([...], shell=False) with an argument list; validate each argument
    tests/test_two_line.py:29  OS command with a shell (CWE-78)  [test]
      os.system(fixed)                                        # SAFE: no value assembled in
      -> subprocess.run([...], shell=False) with an argument list; validate each argument
    tests/test_two_line.py:33  eval / exec of dynamic code (CWE-95)  [test]
      eval(src)                                               # FIND:CWE-95
      -> no eval/exec on data; use ast.literal_eval for literals, a dispatch table for names
    tests/test_two_line.py:33  code assembled from strings, evaluated below (CWE-95)  [test]
      src = "1 + " + expr  ...  eval(src)                               
      -> never eval assembled code; a dispatch table
    tests/test_two_line.py:34  eval / exec of dynamic code (CWE-95)  [test]
      exec(src)                                               # FIND:CWE-95
      -> no eval/exec on data; use ast.literal_eval for literals, a dispatch table for names
    tests/test_two_line.py:34  code assembled from strings, evaluated below (CWE-95)  [test]
      src = "1 + " + expr  ...  exec(src)                               
      -> never eval assembled code; a dispatch table
    tests/test_two_line.py:38  path assembled from strings, opened below (CWE-22)  [test]
      path = "/srv/files/" + name  ...  open(path)                              
      -> resolve against a base directory and reject anything outside it
    tests/test_two_line.py:40  path assembled from strings, opened below (CWE-22)  [test]
      path2 = os.path.join(BASE, name)  ...  send_file(path2)                        
      -> resolve against a base directory and reject anything outside it
    tests/test_two_line.py:51  template assembled from strings, rendered below (CWE-1336)  [test]
      text = "Hello {{ " + name + " }}"  ...  Template(text).render()                 
      -> render a file template with a context
    tests/test_two_line.py:52  template assembled from strings, rendered below (CWE-1336)  [test]
      text = "Hello {{ " + name + " }}"  ...  render_template_string(text)            
      -> render a file template with a context
    tests/test_two_line.py:67  eval / exec of dynamic code (CWE-95)  [test]
      exec(cmd);                                                // FIND:CWE-78
      -> no eval/exec on data; use ast.literal_eval for literals, a dispatch table for names
    tests/test_two_line.py:67  code assembled from strings, evaluated below (CWE-95)  [test]
      const cmd = "ls " + name;  ...  exec(cmd);                              
      -> never eval assembled code; a dispatch table
    tests/test_two_line.py:98  code assembled from strings, evaluated below (CWE-95)  [test]
      String cmd = "ls " + name;  ...  Runtime.getRuntime().exec(cmd);         
      -> never eval assembled code; a dispatch table
    ... 4 more

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
    tests/test_two_line.py:58  SQL built from strings, executed below (CWE-89)  [test]
      q = "SELECT * FROM t WHERE id = " + host  ...  cur.execute(q)                          
      -> PreparedStatement / parameters with ? placeholders; never concatenate values into the statement
    tests/test_two_line.py:87  SQL built from strings, executed below (CWE-89)  [test]
      const sql = `SELECT * FROM t WHERE n = ${name}`;  ...  db.query(sql);                          
      -> PreparedStatement / parameters with ? placeholders; never concatenate values into the statement
    tests/test_two_line.py:106  SQL built from strings, executed below (CWE-89)  [test]
      String q = "SELECT * FROM t WHERE n = " + name;  ...  stmt.executeQuery(q);                   
      -> PreparedStatement / parameters with ? placeholders; never concatenate values into the statement

  VUL-WEB-001  (not in register)  [register: ?]
    tests/test_two_line.py:47  HTML marked safe (CWE-79)  [test]
      return Markup(html)                                     # FIND:CWE-79
      -> let the template engine escape; sanitise (bleach) before marking safe
    tests/test_two_line.py:47  HTML assembled from strings, sent below (CWE-79)  [test]
      html = "<b>" + name + "</b>"  ...  return Markup(html)                     
      -> escape on output; never build HTML from values
    tests/test_two_line.py:52  HTML marked safe (CWE-79)  [test]
      render_template_string(text)                            # FIND:CWE-1336
      -> let the template engine escape; sanitise (bleach) before marking safe

  VUL-INPUT-001  (not in register)  [register: ?]
    .aix/scripts/extern.py:41  URL assembled from strings, requested below (CWE-918)  [accepted: VUL-INPUT-001 host fixed to codeload.github.com; repo and branch come from the kit's own registry.json (VUL-DEP-002)]
      url = f"https://codeload.github.com/{repo}/tar.gz/refs/heads/{branch}"  ...  data = urllib.request.urlopen(url, timeo
    tests/test_two_line.py:56  URL assembled from strings, requested below (CWE-918)  [test]
      target = "https://" + host + "/api"  ...  requests.get(target)                    
      -> allow-list hosts; block private ranges and redirects

  VUL-WEB-003  (not in register)  [register: ?]
    tests/test_js_taint.py:56  open redirect from input (CWE-601)  [test]
      res.redirect(req.query.next);                                 // FIND:CWE-601
      -> allow-list redirect targets or use relative paths only

  skipped by marker: .aix/scripts/securityrules.py  (aix: skip-security-scan ` in a file's head.""")
  skipped by marker: .aix/scripts/vulnerabilities.py  (aix: skip-security-scan this file describes sources and sinks and holds the self-test snippets""")
  skipped by marker: .aix/scripts/codesecurity.py  (aix: skip-security-scan this file holds the rule patterns and the known-bad self-test snippets""")
  no pattern matched for: VUL-AI-001, VUL-AI-002, VUL-AUTHN-001, VUL-AUTHN-002, VUL-DEP-001, VUL-INFRA-001, VUL-INPUT-002, VUL-LOG-001, VUL-SECRET-001, VUL-SECRET-002, VUL-WEB-002  (rules ran; absence of a match is not evidence of absence)
  next: review each REVIEW line; fix or mark `# aix: accepted VUL-… <why>`; `aix code security --audit` writes the audit report;
        then `aix docs security` / the security-audit-* skills move register rows on that evidence.
```
