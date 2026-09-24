aix docs validate

Are the DOCS right? Exit 1 on errors. Checks every markdown file under docs/ and skills/:
  - front-matter present; skill `name` equals its folder path
  - every folder has an INDEX.md and every file is listed in it
  - every referenced ID (FR/NFR/API/DM/ADR/TS/VUL/TASK/CONFLICT) exists; relative links resolve
  - test specs cover existing requirements; vulnerability statuses are valid
  - API/DM field names appear in the field dictionary
  - STATUS DRIFT: FR/NFR/API `implemented`/`verified` need an @implements marker in code, TS `automated` needs
    @tests, VUL `mitigated` needs @mitigates, and any VUL status beyond `expected` needs an audit report
    (`accepted` also an ADR). A doc may not claim more than the code and the evidence show.
Run before every hand-off and in CI. `aix doctor` is the counterpart for the installation.
