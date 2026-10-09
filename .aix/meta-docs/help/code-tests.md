aix code tests [PATH...] [--untested] [--gate] [--report]
               | --priority [--top N] | --affected [--base REF] [--plain]

TESTS SEEN FROM THE CODE. Every folder that holds code is a module, and every module needs its own tests.

  (no option)     the module tree; each module with the test files that import one of its files directly, or
                  NO TESTS. A test reaching only a module's parent or children does not count for it. Inline tests
                  count: Rust `#[cfg(test)]`, ABAP `FOR TESTING`. A folder that only holds other modules is shown
                  as their container. Test files that import no module (end-to-end over HTTP, a subprocess) are
                  counted and credited to none.
  --untested      only the modules without their own tests, one per line
  --gate          exit 1 on any untested module (the advised `module-tests` step of standard and release)
  --report        also write docs/tests/tests-by-module.md

  --priority [--top N]   the functions to test first (default top 20), from the call graph (aix code graph --functions):
      paths       the call paths that end in it: every caller and every branch through every caller (A calls B
                  and C, both call D: D has 4); functions calling each other in a loop count as one
      cognitive   its cognitive complexity (aix code style)
      score       (paths + 1) x cognitive: a simple function on many paths ranks below a complex one on fewer
                  (the +1 is the function itself, so a complex entry point called from outside still ranks)
      test        tested: a test calls it directly (by the call graph, or by name in a file the test imports);
                  touched: a test reaches it only through other functions; no test: neither
    Not directly tested functions come first, by score.

  --affected [--base REF] [--plain]   the tests a change reaches (aix code affected)

What the graph cannot see a test cannot be credited for: a test over HTTP or a subprocess, a fixture loaded by
name, a call through an interface the tool cannot resolve to its implementation. Reach counts only calls the
graph resolves (the report of aix code graph --functions says how many). Paths are counted in the code, not at run
time: a call inside a loop that runs a thousand times is one path.
