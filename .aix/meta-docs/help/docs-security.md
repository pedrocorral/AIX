aix docs security [open|validated] [--gate]

Where does the vulnerability register stand? Reads docs/security/vulnerability-register.md and the audit reports.
  NOT VALIDATED   rows still expected / unverified / confirmed / mitigated, worst first, with the audit skill to run
  VALIDATED       addressed with evidence, accepted by ADR, or not-applicable
  PROBLEM         a status beyond `expected` with no audit report mentioning the VUL (or `accepted` without ADR)
  --gate          release check: exit 1 if any row is open or lacks evidence
The audits themselves are done by the security-audit-* skills; this only reports and gates.
