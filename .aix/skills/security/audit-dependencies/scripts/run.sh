#!/usr/bin/env bash
# Runs whatever dependency auditors are installed; prints a compact summary per ecosystem.
set -u
run(){ echo; echo "## $1"; shift; "$@" 2>&1 | tail -40; }
if ls pyproject.toml requirements*.txt backend/pyproject.toml backend/requirements*.txt >/dev/null 2>&1; then
  command -v pip-audit >/dev/null && run "pip-audit" pip-audit || echo "pip-audit not installed (pip install pip-audit)"
fi
if ls package-lock.json frontend/package-lock.json >/dev/null 2>&1; then
  d=$( [ -f frontend/package-lock.json ] && echo frontend || echo . ); run "npm audit ($d)" npm --prefix "$d" audit --audit-level=moderate
fi
command -v osv-scanner >/dev/null && run "osv-scanner" osv-scanner -r . || echo "osv-scanner not installed (optional, covers all lockfiles)"
command -v trivy >/dev/null && ls Dockerfile infra/Dockerfile* >/dev/null 2>&1 && run "trivy config" trivy config . || true
echo; echo "## lockfiles present"; ls uv.lock poetry.lock Pipfile.lock package-lock.json pnpm-lock.yaml yarn.lock backend/uv.lock backend/poetry.lock frontend/package-lock.json 2>/dev/null || echo "NONE — VUL-DEP-001 confirmed"
echo; echo "Done. Each high/critical finding → task; record versions in the audit report."
