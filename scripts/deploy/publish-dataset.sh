#!/usr/bin/env bash
# Import one canonical dataset. This does not build or restart the web image.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib.sh
source "$HERE/lib.sh"
require_cmd docker python3

file=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --file) file="$2"; shift 2 ;;
    *) die "unknown argument: $1" ;;
  esac
done
[[ -n "$file" && -f "$file" ]] || die "usage: publish-dataset.sh --file canonical.json"
"$HERE/check-env.sh" "$ENV_FILE"
load_env_file
python3 - "$file" <<'PY'
import json, sys
document = json.load(open(sys.argv[1], encoding="utf-8"))
kind = document.get("dataset_kind")
if kind != "live":
    sys.exit(f"refusing dataset_kind {kind!r}; production import accepts a live canonical file")
PY

prepare_state
image="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["image"])' "$STATE_DIR/current.json" 2>/dev/null || true)"
[[ -n "$image" ]] || image="${PDOOM_WEB_IMAGE}"
backup_path="$(PDOOM_PG_CONTAINER=pdoom-prod-postgres POSTGRES_DB="$POSTGRES_DB" PDOOM_BACKUP_DIR="$PDOOM_BACKUP_DIR" "$ROOT/scripts/backup/backup.sh")"
echo "pre_import_backup=$backup_path"
if ! docker run --rm --network pdoom-prod \
  -v "$file:/dataset.json:ro" \
  -e NODE_ENV=production \
  -e PDOOM_ENV=production \
  -e APP_BASE_URL="$APP_BASE_URL" \
  -e DATABASE_URL="$DATABASE_URL" \
  -e PDOOM_MIGRATIONS_DIR=/app/migrations \
  "$image" \
  node /app/pdoom-cli.mjs import /dataset.json; then
  echo "import failed; the import transaction rolls back. Backup: $backup_path" >&2
  exit 1
fi
dataset_id="$(docker exec -u postgres pdoom-prod-postgres psql --username "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT dataset_id FROM dataset_imports WHERE is_current")"
python3 - "$STATE_DIR/last-import.json" "$backup_path" "$dataset_id" <<'PY'
import json, sys
path, backup, dataset_id = sys.argv[1:]
with open(path, "w", encoding="utf-8") as handle:
    json.dump({"backup": backup, "dataset_id": dataset_id.strip()}, handle, indent=2)
    handle.write("\n")
PY
echo "imported dataset_id=${dataset_id//[[:space:]]/} backup=$backup_path"
