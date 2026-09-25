# Code security (generated — do not edit)

```
Code security — .aix/scripts, tests

  findings to review 0; in tests (not gated, --strict to gate) 21; accepted in code 1; register rows with rules 16, with findings 4
  A match is a finding to review, not proof of exploitability; a clean row is not proof of absence.

  VUL-INJ-002  (not in register)  [register: ?]
    tests/test_two_line.py:15  command assembled from strings, run with a shell below (CWE-78)  [test]
      cmd = "ls " + name  ...  os.system(cmd)                          
      -> argument list without a shell; validate each argument
    tests/test_two_line.py:17  command assembled from strings, run with a shell below (CWE-78)  [test]
      cmd2 = f"ls {name}"  ...  subprocess.run(cmd2, shell=True)        
      -> argument list without a shell; validate each argument
    tests/test_two_line.py:19  command assembled from strings, run with a shell below (CWE-78)  [test]
      cmd3 = "ls {}".format(name)  ...  subprocess.run(cmd3, shell=True)        
      -> argument list without a shell; validate each argument
    tests/test_two_line.py:21  command assembled from strings, run with a shell below (CWE-78)  [test]
      cmd4 = "ls %s" % name  ...  subprocess.check_output(cmd4, shell=True
      -> argument list without a shell; validate each argument
    tests/test_two_line.py:33  code assembled from strings, evaluated below (CWE-95)  [test]
      src = "1 + " + expr  ...  eval(src)                               
      -> never eval assembled code; a dispatch table
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
    tests/test_two_line.py:67  code assembled from strings, evaluated below (CWE-95)  [test]
      const cmd = "ls " + name;  ...  exec(cmd);                              
      -> never eval assembled code; a dispatch table
    tests/test_two_line.py:98  code assembled from strings, evaluated below (CWE-95)  [test]
      String cmd = "ls " + name;  ...  Runtime.getRuntime().exec(cmd);         
      -> never eval assembled code; a dispatch table
    tests/test_two_line.py:134  OS command with a shell (CWE-78)  [test]
      FAR = "\n" + "def far(name):\n    cmd = 'ls ' + name\n" + "    x = 1\n" * 45 + "    os.system(cmd)            
      -> subprocess.run([...], shell=False) with an argument list; validate each argument
    tests/test_two_line.py:134  command assembled from strings, run with a shell below (CWE-78)  [test]
      let cmd = format!("ls {}", name);  ...  FAR = "\n" + "def far(name):\n    cmd = 
      -> argument list without a shell; validate each argument
    tests/test_two_line.py:138  command assembled from strings, run with a shell below (CWE-78)  [accepted: VUL-INJ-002 reviewed, name is an enum value]
      cmd = "ls " + name  ...  os.system(cmd)   # FIND:CWE-78 aix: acce

  VUL-INJ-001  Paths from config (`code_roots`, sources) used in file operations with  [register: expected]
    tests/fixtures/java-app/src/main/java/com/acme/app/Repo.java:6  SQL built from strings, executed below (CWE-89)  [test]
      String q = "SELECT * FROM t WHERE id = " + id;  ...  return DriverManager.getConnection("jdbc
      -> PreparedStatement / parameters with ? placeholders; never concatenate values into the statement
    tests/test_js_taint.py:46  SQL built from strings, executed below (CWE-89)  [test]
      const sql = "SELECT * FROM users WHERE id = " + id;  ...  await db.query(sql);                    
      -> PreparedStatement / parameters with ? placeholders; never concatenate values into the statement
    tests/test_two_line.py:58  SQL built from strings, executed below (CWE-89)  [test]
      q = "SELECT * FROM t WHERE id = " + host  ...  cur.execute(q)                          
      -> PreparedStatement / parameters with ? placeholders; never concatenate values into the statement
    tests/test_two_line.py:87  SQL built from strings, executed below (CWE-89)  [test]
      const sql = `SELECT * FROM t WHERE n = ${name}`;  ...  db.query(sql);                          
      -> PreparedStatement / parameters with ? placeholders; never concatenate values into the statement
    tests/test_two_line.py:106  SQL built from strings, executed below (CWE-89)  [test]
      String q = "SELECT * FROM t WHERE n = " + name;  ...  stmt.executeQuery(q);                   
      -> PreparedStatement / parameters with ? placeholders; never concatenate values into the statement

  VUL-INPUT-001  (not in register)  [register: ?]
    tests/test_two_line.py:56  URL assembled from strings, requested below (CWE-918)  [test]
      target = "https://" + host + "/api"  ...  requests.get(target)                    
      -> allow-list hosts; block private ranges and redirects

  VUL-WEB-001  (not in register)  [register: ?]
    tests/test_two_line.py:47  HTML assembled from strings, sent below (CWE-79)  [test]
      html = "<b>" + name + "</b>"  ...  return Markup(html)                     
      -> escape on output; never build HTML from values

  skipped by marker: .aix/scripts/securityrules.py  (aix: skip-security-scan ` in a file's head.""")
  skipped by marker: .aix/scripts/vulnerabilities.py  (aix: skip-security-scan this file describes sources and sinks and holds the self-test snippets""")
  skipped by marker: .aix/scripts/codesecurity.py  (aix: skip-security-scan this file holds the rule patterns and the known-bad self-test snippets""")
  no pattern matched for: VUL-AI-001, VUL-AI-002, VUL-AUTHN-001, VUL-AUTHN-002, VUL-DEP-001, VUL-INFRA-001, VUL-INPUT-002, VUL-LOG-001, VUL-SECRET-001, VUL-SECRET-002, VUL-WEB-002, VUL-WEB-003  (rules ran; absence of a match is not evidence of absence)
  next: review each REVIEW line; fix or mark `# aix: accepted VUL-… <why>`; `aix code security --audit` writes the audit report;
        then `aix docs security` / the security-audit-* skills move register rows on that evidence.
```
