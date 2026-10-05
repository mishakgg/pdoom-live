#!/usr/bin/env bash
# One bounded refresh. Does not import, publish, or enable a timer.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export PYTHONPATH="$ROOT/pipeline${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m pdoom_pipeline.jobs.refresh --once "$@"
