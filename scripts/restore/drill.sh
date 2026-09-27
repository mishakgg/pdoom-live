#!/usr/bin/env bash
# Backup, restore, failed-migration, and bad-import drill against a throwaway database.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
IMAGE="${PDOOM_IMAGE:-pdoom-live:ci}"
LIVE="${PDOOM_DRILL_DATASET:-$ROOT/data/collections/cohort-v2026-09/canonical-live.json}"
NET="pdoom-drill-$$"
PG="pdoom-drill-pg-$$"
WORK="$(mktemp -d)"
PASSWORD="drill-password-value"
cleanup() {
  docker rm -f "$PG" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

docker image inspect "$IMAGE" >/dev/null
[[ -f "$LIVE" ]] || { echo "missing dataset $LIVE" >&2; exit 1; }
docker network create "$NET" >/dev/null
docker run -d --name "$PG" --network "$NET" \
  -e POSTGRES_USER=pdoom \
  -e POSTGRES_PASSWORD="$PASSWORD" \
  -e POSTGRES_DB=pdoom_ops_drill \
  postgres:16 >/dev/null
for _ in $(seq 1 40); do
  docker exec "$PG" pg_isready -U pdoom -d pdoom_ops_drill >/dev/null 2>&1 && break
  sleep 1
done
docker exec "$PG" pg_isready -U pdoom -d pdoom_ops_drill >/dev/null

db_url="postgresql://pdoom:${PASSWORD}@${PG}:5432/pdoom_ops_drill"
run_cli() {
  docker run --rm --network "$NET" \
    -e NODE_ENV=production \
    -e PDOOM_ENV=production \
    -e APP_BASE_URL=http://127.0.0.1:3000 \
    -e DATABASE_URL="$db_url" \
    -e PDOOM_MIGRATIONS_DIR=/app/migrations \
    "$IMAGE" \
    node /app/pdoom-cli.mjs "$@"
}

snapshot() {
  local database="$1"
  docker exec -u postgres "$PG" psql -d "$database" -tAc "
    SELECT json_build_object(
      'organizations', (SELECT count(*) FROM organizations),
      'people', (SELECT count(*) FROM people),
      'sources', (SELECT count(*) FROM sources),
      'source_items', (SELECT count(*) FROM source_items),
      'statements', (SELECT count(*) FROM statements),
      'dataset_id', (SELECT dataset_id FROM dataset_imports WHERE is_current),
      'migrations', (SELECT coalesce(string_agg(version, ',' ORDER BY version), '') FROM schema_migrations),
      'sample_name', (SELECT display_name FROM people ORDER BY slug LIMIT 1)
    );
  "
}

run_cli migrate
docker run --rm --network "$NET" \
  -e NODE_ENV=production -e PDOOM_ENV=production \
  -e APP_BASE_URL=http://127.0.0.1:3000 \
  -e DATABASE_URL="$db_url" \
  -e PDOOM_MIGRATIONS_DIR=/app/migrations \
  -v "$LIVE:/dataset.json:ro" \
  "$IMAGE" node /app/pdoom-cli.mjs import /dataset.json >/dev/null
good="$(snapshot pdoom_ops_drill)"
printf '%s\n' "$good" >"$WORK/good.json"

backup_started="$(date +%s%3N)"
backup="$(PDOOM_PG_CONTAINER="$PG" POSTGRES_DB=pdoom_ops_drill PDOOM_BACKUP_DIR="$WORK/backups" PDOOM_APP_COMMIT=drill "$ROOT/scripts/backup/backup.sh")"
backup_ms="$(( $(date +%s%3N) - backup_started ))"
bytes="$(stat -c %s "$backup")"
(
  cd "$(dirname "$backup")"
  sha256sum -c "$(basename "$backup" .dump).sha256"
) >/dev/null
echo "backup_bytes=$bytes backup_ms=$backup_ms"

python3 - "$LIVE" "$WORK/mutated.json" "$WORK/slug" "$WORK/original-name" <<'PY'
import json, sys
document = json.load(open(sys.argv[1], encoding="utf-8"))
person = document["people"][0]
open(sys.argv[3], "w", encoding="utf-8").write(person["slug"])
open(sys.argv[4], "w", encoding="utf-8").write(person["display_name"])
person["display_name"] = "Ops Drill Mutated"
json.dump(document, open(sys.argv[2], "w", encoding="utf-8"))
PY
slug="$(cat "$WORK/slug")"
original_name="$(cat "$WORK/original-name")"
[[ "$slug" =~ ^[a-z0-9-]+$ ]] || { echo "drill slug is invalid" >&2; exit 1; }
docker run --rm --network "$NET" \
  -e NODE_ENV=production -e PDOOM_ENV=production \
  -e APP_BASE_URL=http://127.0.0.1:3000 \
  -e DATABASE_URL="$db_url" \
  -e PDOOM_MIGRATIONS_DIR=/app/migrations \
  -v "$WORK/mutated.json:/dataset.json:ro" \
  "$IMAGE" node /app/pdoom-cli.mjs import /dataset.json >/dev/null
changed_name="$(docker exec -u postgres "$PG" psql -d pdoom_ops_drill -tAc "SELECT display_name FROM people WHERE slug = '$slug'")"
changed_name="$(echo "$changed_name" | tr -d '[:space:]')"
[[ "$changed_name" == "OpsDrillMutated" || "$changed_name" == "Ops Drill Mutated" ]] || {
  echo "mutated import left name [$changed_name]" >&2
  exit 1
}

restore_started="$(date +%s%3N)"
"$ROOT/scripts/restore/restore.sh" --container "$PG" --backup "$backup" --target-db pdoom_ops_restored
restore_ms="$(( $(date +%s%3N) - restore_started ))"
restored="$(snapshot pdoom_ops_restored)"
python3 - "$good" "$restored" <<'PY'
import json, sys
if json.loads(sys.argv[1]) != json.loads(sys.argv[2]):
    sys.exit("restored database does not match the backup snapshot")
PY
echo "restore_ms=$restore_ms"

"$ROOT/scripts/restore/restore.sh" --container "$PG" --backup "$backup" --target-db pdoom_ops_drill --confirm-replace
replaced="$(snapshot pdoom_ops_drill)"
python3 - "$good" "$replaced" <<'PY'
import json, sys
if json.loads(sys.argv[1]) != json.loads(sys.argv[2]):
    sys.exit("replaced database does not match the backup snapshot")
PY
restored_name="$(docker exec -u postgres "$PG" psql -d pdoom_ops_drill -tAc "SELECT display_name FROM people WHERE slug = '$slug'")"
python3 - "$original_name" "$restored_name" <<'PY'
import sys
if sys.argv[1].strip() != sys.argv[2].strip():
    sys.exit(f"restore left {sys.argv[2]!r} instead of {sys.argv[1]!r}")
PY

set +e
invalid="$(docker run --rm --network "$NET" \
  -e NODE_ENV=production -e PDOOM_ENV=production \
  -e APP_BASE_URL=http://127.0.0.1:3000 \
  -e DATABASE_URL="$db_url" \
  -e PDOOM_MIGRATIONS_DIR=/app/migrations \
  -v "$WORK/mutated.json:/dataset.json:ro" \
  "$IMAGE" node /app/pdoom-cli.mjs import /no-such.json 2>&1)"
invalid_code=$?
set -e
[[ "$invalid_code" -ne 0 ]] || { echo "invalid import succeeded" >&2; exit 1; }
after_invalid="$(snapshot pdoom_ops_drill)"
python3 - "$good" "$after_invalid" <<'PY'
import json, sys
if json.loads(sys.argv[1]) != json.loads(sys.argv[2]):
    sys.exit("failed import changed the database")
PY

mkdir -p "$WORK/bad-migrations"
printf 'SELECT missing_ops_drill_relation;\n' >"$WORK/bad-migrations/999_ops_bad.sql"
set +e
bad_migration="$(docker run --rm --network "$NET" \
  -e NODE_ENV=production -e PDOOM_ENV=production \
  -e APP_BASE_URL=http://127.0.0.1:3000 \
  -e DATABASE_URL="$db_url" \
  -e PDOOM_MIGRATIONS_DIR=/migrations \
  -v "$WORK/bad-migrations:/migrations:ro" \
  "$IMAGE" node /app/pdoom-cli.mjs migrate 2>&1)"
bad_code=$?
set -e
[[ "$bad_code" -ne 0 ]] || { echo "bad migration succeeded" >&2; exit 1; }
recorded="$(docker exec -u postgres "$PG" psql -d pdoom_ops_drill -tAc "SELECT count(*) FROM schema_migrations WHERE version = '999_ops_bad.sql'")"
[[ "$(echo "$recorded" | tr -d '[:space:]')" == "0" ]] || { echo "failed migration was recorded" >&2; exit 1; }
after_migration="$(snapshot pdoom_ops_drill)"
python3 - "$good" "$after_migration" <<'PY'
import json, sys
if json.loads(sys.argv[1]) != json.loads(sys.argv[2]):
    sys.exit("failed migration changed the database")
PY

empty="$WORK/empty-backups"
mkdir -p "$empty"
set +e
"$ROOT/scripts/backup/backup.sh" --container pdoom-missing-container --database pdoom_ops_drill --output-dir "$empty" >/dev/null 2>&1
missing_code=$?
set -e
[[ "$missing_code" -ne 0 ]] || { echo "backup against a missing container succeeded" >&2; exit 1; }
if find "$empty" \( -name '*.dump' -o -name '*.sha256' -o -name '*.manifest.json' \) | grep -q .; then
  echo "failed backup left a final artifact" >&2
  exit 1
fi

echo "drill_ok backup_bytes=$bytes restore_ms=$restore_ms"
