---
id: aix/agents/authority
description: "Which document wins when two disagree: ADRs, requirements, test and security specs, code, generated artefacts."
block: true
order: 10
section: "Authority order (higher wins)"
---
1. Accepted ADRs (`docs/requirements/decisions/`)  2. Approved requirements & contracts (`docs/requirements/`)
3. Accepted test & security specs (`docs/tests/`, `docs/security/`)  4. Source code  5. Generated artefacts
