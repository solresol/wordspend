#!/bin/sh
set -eu
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
REPO_DIR="${WORDSPEND_REPO_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)}"
cd "$REPO_DIR"
mkdir -p logs
exec 9>logs/pipeline.lock
flock -n 9 || { echo 'Another pipeline is running.' >&2; exit 1; }
if [ "${WORDSPEND_SKIP_PULL:-0}" != 1 ]; then
    if [ -n "$(git status --porcelain)" ]; then
        echo 'Service checkout is dirty; refusing to build an unrecorded revision.' >&2
        exit 1
    fi
    git pull --ff-only
fi
# Pull before loading Python code or resolving the lockfile's dependencies.
export WORDSPEND_PIPELINE_LOCK_FD=9
exec uv run python scripts/run_pipeline.py
