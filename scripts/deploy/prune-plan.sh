#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib.sh
source "$HERE/lib.sh"
[[ $# -eq 2 ]] || die "usage: prune-plan.sh CURRENT_SHA PREVIOUS_SHA"
images_to_remove "$1" "$2"
