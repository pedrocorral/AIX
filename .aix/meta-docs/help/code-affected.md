aix code affected [PATH...] [--base REF] [--plain]

THE TESTS A CHANGE REACHES. Every test file that imports a changed file, directly or through other files, by the
same module graph as aix code graph (Python, JS/TS, Rust, Java, ABAP). Run those first instead of the whole suite.

  (no option)     the change against HEAD: committed differences, staged, unstaged and untracked files
  --base REF      against a commit or a branch: `--base main` covers everything a branch changed
  --plain         only the test paths, one per line:  pytest $(aix code affected --plain)

The report groups the tests by the isolation of the changed file (aix code isolations) when the project declares
any, lists the changed source files no test reaches (nothing guards them: a test to write), and counts the changed
files the graph does not read (docs, config, assets). A changed test file is affected itself.

What the graph cannot see, a test cannot be selected by: a fixture loaded by name (pytest conftest), a plugin, a
file read at run time, a test that reaches code over HTTP. Run the whole suite before closing a task or a release.
