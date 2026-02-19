#!/usr/bin/env bash

set -euo pipefail

if ! command -v rg >/dev/null 2>&1; then
    echo "ripgrep (rg) is required to run this check."
    exit 2
fi

OFFENDERS="$(rg --files -g "*.md" | sed 's|\\|/|g' | tr -d '\r' | rg -v "^(docs/|README\.md)$" || true)"

if [ -n "${OFFENDERS}" ]; then
    echo "Markdown files found outside docs/ (except README.md):"
    echo "${OFFENDERS}"
    exit 1
fi

echo "Docs layout check passed."
