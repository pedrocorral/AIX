# Code vulnerabilities (generated — do not edit)

```
Code vulnerabilities — .aix/scripts, tests

  taint paths (Python): 4 finding(s)  (input sources followed to sinks, one call deep, per file)
    VUL-INJ-002    [register: ?]
      .aix/scripts/selfinstall.py:24  input reaches file path (CWE-22)  [accepted: the person's own HOME, SHELL and PATH decide where their link goes; nothing crosses a trust boundary]
        Path(...) <- os.environ.get()
        -> resolve against a base directory and reject anything outside it
      .aix/scripts/selfinstall.py:29  input reaches file path (CWE-22)  [accepted: the person's own HOME, SHELL and PATH decide where their link goes; nothing crosses a trust boundary]
        Path(...) <- os.environ.get()
        -> resolve against a base directory and reject anything outside it
      .aix/scripts/selfinstall.py:97  input reaches file path (CWE-22)  [accepted: the person's own HOME, SHELL and PATH decide where their link goes; nothing crosses a trust boundary]
        Path(...) <- os.environ.get()
        -> resolve against a base directory and reject anything outside it
      .aix/scripts/selfinstall.py:157  input reaches file path (CWE-22)  [accepted: the person's own HOME, SHELL and PATH decide where their link goes; nothing crosses a trust boundary]
        Path(...) <- found = ... from path = ... from os.environ.get() (line 153) (line 154)
        -> resolve against a base directory and reject anything outside it

  secrets in git history: 0 finding(s)  (last 300 commits, all branches)

  A taint path is static evidence that input can reach a sink, not a proof of exploitability in production;
  a CVE applies to the version, not necessarily to how you use it; a history leak is real until the secret is rotated.
  Fix: taint -> the code (see advice) ; CVE -> upgrade ; history -> rotate now.  `--audit` writes the evidence report.
```
