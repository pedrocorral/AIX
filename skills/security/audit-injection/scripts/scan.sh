#!/usr/bin/env bash
# Deterministic injection-risk scan. Prints file:line hits only; reason about the hits, not the codebase.
# Usage: scan.sh [paths...]  (default: backend src app)
set -u
ROOTS=("$@"); [ ${#ROOTS[@]} -eq 0 ] && ROOTS=(backend src app)
EX='--exclude-dir=node_modules --exclude-dir=.venv --exclude-dir=venv --exclude-dir=__pycache__ --exclude-dir=dist --exclude-dir=build --exclude-dir=migrations'
p(){ echo; echo "## $1"; shift; grep -rnE $EX "$@" "${ROOTS[@]}" 2>/dev/null | head -50; }
p "String-built SQL (f-strings / format / concat near execute)" 'execute\((f"|f'"'"'|.*\+|.*%|.*\.format\()'
p "Raw query helpers with interpolation" '(text|raw|query)\((f"|f'"'"'|.*\.format\(|.*\+)'
p "Shell execution" 'subprocess\.(call|run|Popen)\(.*shell\s*=\s*True|os\.(system|popen)\(|exec\(|eval\('
p "Template / expression injection" 'render_template_string|Template\(.*request|jinja2\.Template\('
p "Path handling with user input" '(open|Path|os\.path\.join)\(.*(request|params|args|form|payload|body)'
p "NoSQL operator injection" '\$where|\$regex.*(request|params|args)'
p "Deserialisation (check yaml.load uses SafeLoader)" 'pickle\.loads?\(|yaml\.load\(|marshal\.loads?\('
echo; echo "Done. Each hit needs: parameterised alternative, or a documented reason + @mitigates VUL-INJ-* at the control."
