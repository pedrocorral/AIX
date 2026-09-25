aix code graph | complexity | dead | clones | style | security | vulnerabilities | stats   [TARGET...] [--gate] [--report]

Three tools on one engine (.aix/scripts/graph.py). All read the same dependency graph of the project's source
(Python, JS/TS, Rust, Java; modules, or functions with --functions); PATH... limits the folders.
  aix code graph      the modularity metric: A (the code) vs B (the ideal shape on the same nodes) = the edits,
                      cycles, upward dependencies, hubs, propagation cost, NCCD, folder Q.  alias: complexity
  aix code dead       dead code: modules no entry point reaches; with --functions, Python functions never referenced
  aix code clones     duplicated functions: exact groups (same structure) and near-clones (--similarity PCT)
  aix code style      readability per function: lines, cognitive/cyclomatic complexity, nesting, parameters,
                      names, docstring, magic numbers; one function = a card with line-numbered advice
  aix code security   static security checks mapped to VUL rows and CWEs; --audit writes the audit evidence
  aix code vulnerabilities  deep checks: Python taint paths, known CVEs (OSV), secrets in git history
  aix code licenses   the licence of every installed dependency, classed; --gate on copyleft, proprietary, unknown
  aix code stats      histogram of function sizes (or any style metric) with mean/sd/percentiles and offenders
  aix code find       which folders hold code: a checklist that sets paths.code_roots in .aix/config.yaml, the
                      default scope of every command above (also run at the end of aix install)
--gate turns each into a CI check; --report writes docs/tests/dependency-graph.md; aix code graph --selftest
proves the arithmetic on known-answer cases. Details: aix help code graph | code dead | code clones | code style | code security | code vulnerabilities | code stats.
