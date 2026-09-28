#!/usr/bin/env bash
# Restore a verified custom-format backup into an explicit database.
# Replacing an existing database requires --confirm-replace.
# Replacing the production database also requires --confirm-production.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../deploy/lib.sh
source "$HERE/../deploy/lib.sh"
require_cmd docker python3 sha256sum

container="${PDOOM_PG_CONTAINER:-pdoom-prod-postgres}"
db_user="${POSTGRES_USER:-pdoom}"
target=""
backup=""
confirm_replace=0
confirm_production=0
production_db="${POSTGRES_DB:-pdoom_live}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --container) container="$2"; shift 2 ;;
    --username) db_user="$2"; shift 2 ;;
    --target-db) target="$2"; shift 2 ;;
    --backup) backup="$2"; shift 2 ;;
    --confirm-replace) confirm_replace=1; shift ;;
    --confirm-production) confirm_production=1; shift ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ -n "$target" && -n "$backup" ]] || die "usage: restore.sh --backup FILE --target-db NAME [--confirm-replace] [--confirm-production]"
valid_db_name "$target" || die "target database name is invalid"
valid_db_name "$db_user" || die "database user is invalid"
valid_db_name "$production_db" || die "production database name is invalid"
[[ "$container" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]+$ ]] || die "container name is invalid"
[[ -f "$backup" ]] || die "backup file is missing"
[[ "$backup" == *.dump ]] || die "backup file must end in .dump"

checksum="${backup%.dump}.sha256"
[[ -f "$checksum" ]] || die "backup checksum is missing"
expected="$(awk '{print $1}' "$checksum")"
name="$(basename "$backup")"
recorded="$(awk '{print $2}' "$checksum")"
[[ "$recorded" == "$name" ]] || die "checksum filename does not match the backup"
actual="$(sha256sum "$backup" | awk '{print $1}')"
[[ "$actual" == "$expected" ]] || die "backup checksum does not match"

exists="$(docker exec -u postgres "$container" psql --username "$db_user" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$target'")"
exists="$(echo "$exists" | tr -d '[:space:]')"
if [[ "$exists" == "1" ]]; then
  [[ "$confirm_replace" -eq 1 ]] || die "database $target already exists; pass --confirm-replace to drop and recreate it"
  if [[ "$target" == "$production_db" && "$confirm_production" -ne 1 ]]; then
    die "refusing to replace production database $target without --confirm-production"
  fi
  docker exec -u postgres "$container" dropdb --username "$db_user" --force "$target"
fi
docker exec -u postgres "$container" createdb --username "$db_user" "$target"
docker exec -i -u postgres "$container" pg_restore --username "$db_user" --single-transaction --exit-on-error --no-owner --dbname "$target" <"$backup"
echo "restored $target"
