#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib.sh
source "$HERE/lib.sh"
[[ $# -eq 3 ]] || die "usage: classify-migrations.sh MIGRATIONS_DIR APPLIED_FILE CLASS_FILE"
classify_migrations "$1" "$2" "$3"
