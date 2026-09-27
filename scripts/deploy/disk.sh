#!/usr/bin/env bash
# Report database, backup, and image disk use. Fail when the backup filesystem is too full.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib.sh
source "$HERE/lib.sh"
require_cmd docker df du

backup_dir="${PDOOM_BACKUP_DIR:-/var/lib/pdoom/backups}"
min_free_mb="${PDOOM_MIN_FREE_MB:-1024}"
[[ "$min_free_mb" =~ ^[0-9]+$ ]] || die "PDOOM_MIN_FREE_MB must be a number"

echo "host:"
df -h /
if [[ -d "$backup_dir" ]]; then
  echo "backup_dir=$backup_dir"
  du -sh "$backup_dir" || true
  avail_kb="$(df -Pk "$backup_dir" | awk 'NR==2 {print $4}')"
  avail_mb="$((avail_kb / 1024))"
  echo "backup_free_mb=$avail_mb"
  if [[ "$avail_mb" -lt "$min_free_mb" ]]; then
    die "backup filesystem has ${avail_mb} MiB free; need ${min_free_mb} MiB"
  fi
else
  echo "backup_dir_missing=$backup_dir"
fi

echo "docker:"
docker system df
if docker volume inspect pdoom-pgdata >/dev/null 2>&1; then
  docker system df -v | awk '/pdoom-pgdata|pdoom-caddy|pdoom-live/ {print}'
fi
