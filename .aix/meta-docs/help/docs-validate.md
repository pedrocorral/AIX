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

Ids (2.21.41): every `id:`, every `covers:`/`affects:`/`related:`/`depends_on:` entry, every `@implements`/`@tests`/
`@mitigates` marker in the code and every id-shaped token in a document's text is checked against the scheme of
conventions/ids-and-traceability.md: the shape of its prefix (`TS-<DOMAIN>-NNN`, `VUL-<CAT>-NNN` with the listed
categories, `ADR-NNNN`, `DM-<Entity>`, …), uppercase, hyphens, the exact digit width, a domain code the glossary's
"Domain code" column defines (when the glossary has one), the file named `<ID>-<kebab-title>.md`, each id defined
once. An invented shape is reported with the rule it breaks and the nearest correct form: `TS-VUL-WEB-002` is four
parts where a test spec has three (a test for a vulnerability takes the domain of what it tests and names the
vulnerability in `covers: [VUL-WEB-002]`), `TS-AUTH-7` wants three digits, `ts-auth-001` is lowercase, `TS_AUTH_001`
uses underscores, `TEST-AUTH-001` and `VULN-INJ-001` are prefixes the scheme does not have. In prose only tokens with a
number count (`VUL` or `TS-SEC` name a family); `TS-*` and `TASK-NNNN` are placeholders.
