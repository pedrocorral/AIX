# security/ — how security is engineered and audited in AIX
Read this when: adding attack surface or running audits. Skip when: pure refactor inside an audited module (still re-audit before closing).

| Path | What | Read when |
|---|---|---|
| `audit-process.md` | Register lifecycle (expected → addressed), audit cadence, evidence, mapping categories → skills | Any audit; closing any task |
| `threat-categories.md` | The category catalogue (INJ, AUTHN, AUTHZ, INPUT, SECRET, DEP, WEB, DATA, LOG, AI, INFRA) with the baseline vulnerabilities every app is assumed to have | Seeding a new project's register; threat modelling |
| `secure-coding-baseline.md` | Non-negotiable defaults every stack must apply | Implementing anything touching input, auth, data |
| `ai-llm-security.md` | Prompt injection, data exfiltration, tool abuse, model supply chain | Any LLM/agent feature |
