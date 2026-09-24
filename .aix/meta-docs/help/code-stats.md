aix code stats [PATH...] [--metric lines|cognitive|cyclomatic|nesting|params] [--report] [--selftest]

THE SHAPE OF THE CODE BASE in one screen: where function sizes sit, how spread they are, and who is pulling the
tail. Uses the same per-function measurements as `aix code style`.

  histogram    fixed bins (1-5, 6-10, 11-20, 21-30, 31-40, 41-60, 61-100, 101-200, 201+ lines), so two projects or
               two dates compare directly; bars scaled to the terminal width, half blocks for resolution; the bin
               holding the limit and every bin above it are marked
  numbers      functions, mean, sample standard deviation, median, p90, p95, max, and how many sit over the
               .aix/config.yaml limit (tests and framework-decorated functions use their adjusted limits)
  offenders    the ten largest functions (* = over its limit); the five files and five folders (depth 2) that push
               the most functions over the limit, with the total excess

Reading it: a healthy code base is right-skewed with a short tail: most functions in 1-20, p90 under the limit,
a handful of large ones you can name. A fat tail or a high sd means size is not being managed; the offender
lists say where to start (`aix code style FILE:FUNCTION` for the card, skill refactor-readability to fix).
--metric switches the whole view to cognitive or cyclomatic complexity, nesting depth or parameter count.
--report writes docs/tests/code-stats.md. Python exact; JS/TS, Rust, Java approximate (as in aix code style).
