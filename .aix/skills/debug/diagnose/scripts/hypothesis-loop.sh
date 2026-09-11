#!/usr/bin/env bash
# Hypothesis loop log: one line per hypothesis, one test per hypothesis. Usage: ./hypothesis-loop.sh "<hypothesis>" "<command that tests it>"
set -euo pipefail
h="$1"; cmd="$2"; log="${DIAG_LOG:-diagnosis.log}"
printf '%s | H: %s | test: %s\n' "$(date -Is)" "$h" "$cmd" >> "$log"
if bash -c "$cmd"; then printf '%s | result: CONFIRMED\n' "$(date -Is)" >> "$log"; else printf '%s | result: refuted\n' "$(date -Is)" >> "$log"; fi
tail -2 "$log"
