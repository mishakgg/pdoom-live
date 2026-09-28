#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib.sh
source "$HERE/lib.sh"
require_cmd python3
file="${1:-$ENV_FILE}"
python3 "$HERE/check_env.py" "$file"
