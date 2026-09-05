# operations/ — running the system: deployment, recovery, incidents
Read this when: deploying, on-call, restoring data, investigating an incident. Skip when: feature work with no deployment impact.

| Path | What | Read when |
|---|---|---|
| `deployment.md` | Environments, promotion flow, rollback, feature flags | Deploying; `infra/` changes |
| `recovery.md` | Backups, restore procedure (tested date), data-loss playbook | Any persistence change; incidents |
| `runbooks/` | One file per recurring operational task or alert | The alert/task in question |
