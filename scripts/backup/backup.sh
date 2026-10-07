#!/usr/bin/env bash
# Write a custom-format PostgreSQL backup, checksum, and manifest.
# A local backup is not disaster recovery until it is copied off the VM.
set -euo pipefail
umask 077
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../deploy/lib.sh
source "$HERE/../deploy/lib.sh"
# shellcheck source=../backup/environment.sh
source "$HERE/../backup/environment.sh"
require_cmd docker python3 sha256sum

container="${PDOOM_PG_CONTAINER:-pdoom-prod-postgres}"
database="${POSTGRES_DB:-pdoom_live}"
db_user="${POSTGRES_USER:-pdoom}"
output_dir="${PDOOM_BACKUP_DIR:-/var/lib/pdoom/backups}"
commit="${PDOOM_APP_COMMIT:-}"
hook="${PDOOM_BACKUP_HOOK:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --container) container="$2"; shift 2 ;;
    --database) database="$2"; shift 2 ;;
    --username) db_user="$2"; shift 2 ;;
    --output-dir) output_dir="$2"; shift 2 ;;
    --commit) commit="$2"; shift 2 ;;
    --hook) hook="$2"; shift 2 ;;
    *) die "unknown argument: $1" ;;
  esac
done

valid_db_name "$database" || die "database name is invalid"
valid_db_name "$db_user" || die "database user is invalid"
[[ "$container" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]+$ ]] || die "container name is invalid"
mkdir -p "$output_dir"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
# mktemp reserves a private per-invocation namespace, even for concurrent jobs
# with the same timestamp. Cleanup can only touch this run's own staging/files.
work="$(mktemp -d "$output_dir/.${database}_${stamp}.XXXXXXXX")"
base="${work##*/}"
base="${base#.}"
partial="$work/archive.dump"
final="$output_dir/${base}.dump"
final_checksum="$output_dir/${base}.sha256"
final_manifest="$output_dir/${base}.manifest.json"
published=()
committed=0
cleanup() {
  rm -rf "$work"
  if [[ "$committed" -ne 1 ]]; then
    local file
    for file in "${published[@]}"; do rm -f "$file"; done
  fi
}
trap cleanup EXIT

if ! docker exec -u postgres "$container" pg_dump --username "$db_user" --format=custom --no-owner --no-acl --dbname "$database" >"$partial"; then
  die "pg_dump failed"
fi
if ! docker exec -i -u postgres "$container" pg_restore --list <"$partial" >/dev/null; then
  die "backup archive is not readable"
fi
bytes="$(stat -c %s "$partial")"
[[ "$bytes" -gt 0 ]] || die "backup archive is empty"

sha="$(sha256sum "$partial" | awk '{print $1}')"
printf '%s  %s\n' "$sha" "${base}.dump" >"$partial.sha256"

migrations="$(docker exec -u postgres "$container" psql --username "$db_user" -d "$database" -tAc "SELECT version FROM schema_migrations ORDER BY version" 2>/dev/null || true)"
dataset_id="$(docker exec -u postgres "$container" psql --username "$db_user" -d "$database" -tAc "SELECT dataset_id FROM dataset_imports WHERE is_current LIMIT 1" 2>/dev/null || true)"
if [[ -z "$commit" && -f "$STATE_DIR/current.json" ]]; then
  commit="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("commit") or "")' "$STATE_DIR/current.json")"
fi

python3 - "$partial.manifest.json" "$database" "$stamp" "$base" "$sha" "$bytes" "$commit" "$dataset_id" "$migrations" <<'PY'
import json, sys
manifest, database, stamp, base, sha, bytes_, commit, dataset_id, migrations = sys.argv[1:]
payload = {
    "database": database,
    "created_at": f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}T{stamp[9:11]}:{stamp[11:13]}:{stamp[13:15]}Z",
    "format": "pg_dump-custom",
    "file": f"{base}.dump",
    "sha256": sha,
    "bytes": int(bytes_),
    "migrations": [line.strip() for line in migrations.splitlines() if line.strip()],
    "app_commit": commit or None,
    "dataset_id": dataset_id.strip() or None,
}
with open(manifest, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
    handle.write("\n")
PY

# Hard links publish without replacing an existing identity. A failed link
# never authorizes cleanup of that existing file; only successful links are ours.
ln -T "$partial" "$final"
published+=("$final")
ln -T "$partial.sha256" "$final_checksum"
published+=("$final_checksum")
ln -T "$partial.manifest.json" "$final_manifest"
published+=("$final_manifest")
committed=1
echo "$final"

if [[ -n "$hook" ]]; then
  [[ -f "$hook" && -x "$hook" && "$hook" == /* ]] || die "backup hook must be an absolute executable file"
  "$hook" "$output_dir" "$final_manifest" >&2
fi
