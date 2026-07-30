#!/usr/bin/env bash
# Run tests against every Python version listed in pyproject.toml's
# `requires-python` range.  Requires `uv` (https://docs.astral.sh/uv/).
set -euo pipefail

VERSIONS=(3.10 3.11 3.12 3.13 3.14)
failures=0

for py in "${VERSIONS[@]}"; do
  echo "── Python $py ──"
  if uv run --python "$py" pytest "$@"; then
    echo "✅ Python $py passed"
  else
    echo "❌ Python $py failed"
    ((failures++))
  fi
  echo
done

if [ "$failures" -gt 0 ]; then
  echo "$failures version(s) failed"
  exit 1
fi

echo "All versions passed"
