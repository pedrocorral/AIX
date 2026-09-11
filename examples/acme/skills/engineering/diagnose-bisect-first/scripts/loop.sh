#!/usr/bin/env bash
# one hypothesis, one test; appends to diagnosis.log
set -euo pipefail
printf '%s | H: %s | test: %s\n' "$(date -Is)" "$1" "$2" >> diagnosis.log
bash -c "$2" && echo CONFIRMED >> diagnosis.log || echo refuted >> diagnosis.log
