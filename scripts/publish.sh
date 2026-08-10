#!/usr/bin/env bash
# Public release (main) update — PDFs + website only.
# Run from the `source` branch after editing markdown:
#   bash scripts/publish.sh
set -euo pipefail
cd "$(dirname "$0")/.."

if [ "$(git branch --show-current)" != "source" ]; then
    echo "Run this from the 'source' branch." >&2
    exit 1
fi

echo "==> Rebuilding PDFs and website..."
make build_pdfs > /dev/null
make site > /dev/null

echo "==> Committing source (latest PDFs + site)..."
git add -A
if git diff --cached --quiet; then
    echo "(no source changes)"
else
    git commit -m "update: regenerate PDFs and website"
    git push origin source
fi

PDFS=$(git -c core.quotepath=off ls-tree -r --name-only source | grep '\.pdf$')

echo "==> Syncing PDFs + docs to main..."
git checkout main
git rm -r --quiet "01-কিবর-ও-উজব" docs assets 2>/dev/null || true
git checkout source -- $PDFS docs
git add -A
if git diff --cached --quiet; then
    echo "(no changes to publish)"
else
    git commit -m "update: regenerate PDFs and website"
    git push origin main
fi
git checkout source
echo "==> Done, back on 'source'."
