# Code style (generated — do not edit)

```
  runtime: Python 3.13 (python on PATH (assumed: nothing in the project declares a version)); Java: version unknown (no pom.xml / build.gradle)
  functions analysed 940; over a limit 0 (lines 0, cognitive 0, cyclomatic 0, nesting 0, params 0, pass-through 0); with any finding 415; files over 400 lines: 0

  FUNCTION                                                     lines  cogn  cycl  nest  prm  findings
  .aix/scripts/stats.py:selftest                                  12     5     5     1    0   single-letter name `d`; public function without a docstring / doc comment
  .aix/scripts/style.py:selftest                                  17     5     8     1    0   public function without a docstring / doc comment; magic number 6
  .aix/scripts/vulnerabilities.py:write_audit                     20    12     9     2    3   public function without a docstring / doc comment; magic number 3
  .aix/scripts/runtime.py:rust                                    11     5     4     2    1   single-letter name `m`; single-letter name `m`
  .aix/scripts/codefind.py:_draw                                  13     3     5     1    3   single-letter name `h`; single-letter name `w`
  .aix/scripts/security.py:rows                                   11     7     6     3    0   single-letter name `c`; magic number 6
  .aix/scripts/vulnerabilities.py:_selftest_checks                17     2     8     1    3   magic number 3; magic number 4
  .aix/scripts/modernise.py:modern_py                             13     5     6     1    2   magic number 3; magic number 3
  .aix/scripts/modernise.py:_modern_js                            13     8     8     2    3   single-letter name `m`; single-letter name `m`
  .aix/scripts/codesecurity.py:_vul_lines                         11     9     6     2    3   magic number 70; magic number 3
  .aix/scripts/codesecurity.py:_classify                           6     3    10     0    2   magic number 3; magic number 7
  .aix/scripts/codesecurity.py:_audit_rows                        11     7     7     3    3   magic number 3; magic number 4
  .aix/scripts/runtime.py:_node_year                               2     6     4     0    1   magic number 14; magic number 18
  .aix/scripts/clones.py:render_clones                            11     2     4     1    2   public function without a docstring / doc comment; magic number 20
  .aix/scripts/secrethistory.py:history                           16     8     9     4    2   single-letter name `h`; magic number 300
  .aix/scripts/stats.py:describe                                  10     3     5     1    1   single-letter name `n`; single-letter name `s`
  .aix/scripts/stats.py:offenders                                 16     8     7     3    4   single-letter name `f`; single-letter name `d`
  .aix/scripts/jstaint.py:_statements                             10     3     6     2    2   single-letter name `i`; single-letter name `j`
  .aix/scripts/roadmap.py:cmd_done                                16     5     6     1    2   single-letter name `p`; single-letter name `t`
  .aix/scripts/security.py:print_group                            10     4     4     1    2   public function without a docstring / doc comment; magic number 20
  .aix/scripts/cvecheck.py:osv_detail                             10     3    10     2    3   single-letter name `r`; single-letter name `v`
  .aix/scripts/deadcode.py:render_dead                            14     3     5     1    4   public function without a docstring / doc comment; magic number 6
  .aix/scripts/codesecurity.py:selftest                            9     4     7     0    0   magic number 3; magic number 4
  .aix/scripts/validate.py:frontmatter                            19    12     6     4    1   single-letter name `t`; public function without a docstring / doc comment
  .aix/scripts/validate.py:check_vul_register                      9     8     7     3    0   public function without a docstring / doc comment; magic number 3
  .aix/scripts/clones.py:find_clones                              12     1     7     1    2   magic number 4; magic number 4
  .aix/scripts/codefind.py:tui                                    12     5     5     2    5   single-letter name `s`; public function without a docstring / doc comment
  .aix/scripts/jstaint.py:taint                                   14    11     8     3    1   magic number 3; magic number 4
  .aix/scripts/roadmap.py:cmd_new                                  7     0     1     0    2   single-letter name `t`; single-letter name `t`
  .aix/scripts/roadmap.py:cmd_block                                6     0     1     0    2   single-letter name `p`; single-letter name `t`
  ... 385 more; narrow the target or use --all
  modernise (2, advice for the detected runtime):
    .aix/scripts/install_skills.py:link_or_copy line 43: `os.path.relpath` -> `pathlib.Path` reads as objects, not string plumbing
    .aix/scripts/selfinstall.py:on_path line 35: `os.path.expanduser` -> `pathlib.Path` reads as objects, not string plumbing
  * = over its limit (gated). Names, docstrings and magic numbers are advice.  Details: aix code style FILE:FUNCTION
  fix with: OVER -> skill refactor-readability (one metric per change); modernise -> refactor-modernise
```
