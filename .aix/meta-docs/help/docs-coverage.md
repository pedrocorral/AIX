aix docs coverage

Regenerates docs/tests/coverage-matrix.md: one row per requirement with the test specs that cover it (`covers:`
in TS files), the code that implements it (@implements markers) and the tests that exercise it (@tests markers),
plus a gap column: `no test spec`, `spec not automated`, `no code`. Pure regex scan, no model. Only as honest as
the markers: `aix docs validate` fails a status that claims more than the markers show.
