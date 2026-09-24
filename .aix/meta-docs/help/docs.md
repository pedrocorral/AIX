aix docs validate | coverage | security

  aix docs validate   are the DOCS right? front-matter, INDEXes, IDs, links, TS -> FR, VUL statuses, field
                      dictionary, status drift (implemented/automated/mitigated without the code marker), VUL
                      evidence. CI gate, exit 1 on errors.
  aix docs coverage   regenerate docs/tests/coverage-matrix.md: requirement -> test spec -> code -> gaps.
  aix docs security   the vulnerability register: validated rows vs not, audit skills still to run, statuses
                      without evidence; --gate is the release check.
Details: aix help docs validate | docs coverage | docs security.
