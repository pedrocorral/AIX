#!/usr/bin/env bash
# aix: skip-security-scan this script holds grep patterns for secrets and injection
# Deterministic secrets/config scan. Uses gitleaks/detect-secrets if present, else regex fallback.
set -u
if command -v gitleaks >/dev/null; then echo "## gitleaks"; gitleaks detect --no-banner --redact -v 2>&1 | tail -40
elif command -v detect-secrets >/dev/null; then echo "## detect-secrets"; detect-secrets scan 2>/dev/null | head -80
else
  echo "## regex fallback (install gitleaks for history scanning)"
  grep -rnEI --exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=.git --exclude=*.lock \
    '(api[_-]?key|secret|password|passwd|token|private[_-]?key)\s*[:=]\s*["'"'"'][^"'"'"']{8,}' . 2>/dev/null | grep -v '.env.example' | head -40
  grep -rnE 'AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY' . --exclude-dir=.git --exclude-dir=node_modules 2>/dev/null | head -20
fi
echo; echo "## tracked env files (should be none)"; git ls-files 2>/dev/null | grep -E '(^|/)\.env(\.|$)' | grep -v '.example'
echo; echo "## .env.example vs settings keys"
[ -f infra/.env.example ] && grep -oE '^[A-Z_]+' infra/.env.example | sort > /tmp/envex.txt && grep -rhoE '(getenv|environ(\.get)?)\(["'"'"'][A-Z_]+' backend 2>/dev/null | grep -oE '[A-Z_]+$' | sort -u > /tmp/envused.txt && comm -13 /tmp/envex.txt /tmp/envused.txt | sed 's/^/undocumented: /'
echo; echo "Done. Findings map to VUL-SECRET-001/002."
