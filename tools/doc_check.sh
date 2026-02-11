#!/bin/bash
# doc_check.sh — Verify file references in documentation
# Flags paths mentioned in markdown docs that don't exist on disk.
# Usage: bash tools/doc_check.sh [file_or_dir]
#   No args: checks docs/ARDEN_CHEAT_SHEET.md
#   With arg: checks specified .md file or all .md in directory

set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || echo /home/xai/Documents/ty_learn)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

target="${1:-docs/ARDEN_CHEAT_SHEET.md}"
if [[ -d "$target" ]]; then
    files=$(find "$target" -name '*.md' -not -path '*/archive/*')
else
    files="$target"
fi

errors=0
checked=0

for doc in $files; do
    # Extract file paths from code blocks, tables, and inline references
    paths=$(grep -oP '(?:actors|core|tools|lib|scripts|docs|data|config|frontend|matching)/[\w/._-]+\.\w+' "$doc" 2>/dev/null | sort -u || true)

    for path in $paths; do
        checked=$((checked + 1))
        if [[ ! -e "$path" ]]; then
            printf "${RED}MISSING${NC}  %-55s (in %s)\n" "$path" "$doc"
            errors=$((errors + 1))
        fi
    done
done

echo ""
echo "Checked ${checked} path references"
if [[ $errors -eq 0 ]]; then
    printf "${GREEN}All references valid.${NC}\n"
else
    printf "${YELLOW}${errors} broken reference(s) found.${NC}\n"
fi
exit $errors
