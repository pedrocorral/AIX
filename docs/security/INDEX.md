# security/ — vulnerability register and audit evidence
Read this when: touching input, auth, data, dependencies, infra, LLM calls; before closing any task; at release. Skip when: never fully — at least grep your component in the register.

| Path | What | Read when |
|---|---|---|
| `vulnerability-register.md` | All `VUL-*` rows with status. **grep by category/component; do not read whole** | Any task with attack surface |
| `audits/` | Audit reports (evidence for status changes) | Verifying a status; scheduled audits |
| (`aix docs security`) | Command: not-validated vs validated rows, audit skills still to run, missing evidence; `--gate` for release | Before auditing; at release |
| `threat-model.md` | Project-specific assets, actors, trust boundaries, data flows | Threat modelling; onboarding to security |
