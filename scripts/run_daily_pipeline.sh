#!/bin/sh
set -eu

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
export WORDSPEND_DATABASE_URL="${WORDSPEND_DATABASE_URL:-dbname=wordspend}"
export PAUSANIAS_DATABASE_URL="${PAUSANIAS_DATABASE_URL:-dbname=pausanias}"

REPO_DIR="${WORDSPEND_REPO_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
DEPLOY_TARGET="${WORDSPEND_DEPLOY_TARGET:-wordspend@merah:/var/www/vhosts/wordspend.symmachus.org/htdocs/}"
IMPORT_PAUSANIAS="${IMPORT_PAUSANIAS:-0}"

cd "$REPO_DIR"
mkdir -p logs build/analysis site

if [ -d .git ]; then
  if git diff --quiet && git diff --cached --quiet; then
    git pull --ff-only -q || true
  else
    echo "Skipping git pull because the checkout is dirty."
  fi
fi

uv run python scripts/init_db.py
uv run python scripts/load_work_catalog.py

if [ "$IMPORT_PAUSANIAS" = "1" ]; then
  uv run python scripts/import_pausanias.py --limit 0
fi

uv run python scripts/run_analysis.py --from-db --save-db --output-dir build/analysis
uv run python scripts/generate_site.py --analysis-dir build/analysis --catalog data/work_catalog.csv --output-dir site
rsync -az --delete site/ "$DEPLOY_TARGET"
