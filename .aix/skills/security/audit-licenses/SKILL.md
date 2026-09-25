---
name: security-audit-licenses
description: Audit the licences of installed dependencies against the product's own licence: classes, unknowns read from LICENSE files, decisions recorded in config and an ADR; VUL-DEP-003, new dependencies, releases.
---
# security-audit-licenses
Read: the register row VUL-DEP-003 (`grep -n "VUL-DEP-003" docs/security/vulnerability-register.md`); the ADR that states the product's own licence (`grep -ril "licence\|license" docs/requirements/decisions/`), or note that none exists.

## Tool first (near-zero tokens)
Run `aix code licenses`. Reason only about its output: every line that is not permissive, and every NOT INSTALLED line.
If the dependencies are not installed, say so and stop: the tool reads metadata on disk, never the network.

## Procedure
1. **Unknown**: open the package's LICENSE / COPYING file (under `.venv/.../site-packages/<pkg>*.dist-info/` or
   `node_modules/<pkg>/`); identify the SPDX id; record it: `licenses_known:` `<package>: <id>` in `.aix/config.yaml`.
   No file at all: treat as proprietary until the maintainer answers; record the question in the task.
2. **Strong copyleft** (GPL, AGPL, SSPL ...): compatible only when the product's own licence is compatible (an ADR says
   which). Compatible: `licenses_allow: [<id>]` with the ADR referenced in the comment. Not compatible: a task to
   replace the dependency; the finding stays open.
3. **Proprietary**: find the terms the team agreed to; record them in an ADR; `licenses_allow:` once recorded.
4. **Weak copyleft** (LGPL, MPL, EPL): allowed as an unmodified library; note it in the ADR; a modified copy is a
   strong-copyleft decision.
5. Re-run `aix code licenses --gate`; it must pass. Write the evidence (the report, the config lines, the ADR) in the
   audit report and move VUL-DEP-003 with it, as `security-audit` does for every row.

## Never
- Decide a licence question from the package name or its README: the LICENSE file and the ADR decide.
- Mark `licenses_allow:` without the reason in the comment: the next reviewer must see why.

## Hand-off
The report, the config lines added, the ADR written or referenced, the tasks opened for replacements.
