#!/usr/bin/env bash
# Switch back to the previous image. Does not reverse migrations.
# A breaking migration requires restoring the pre-migration backup first.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib.sh
source "$HERE/lib.sh"
require_cmd python3

dry_run=0
restore_backup=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) dry_run=1; shift ;;
    --restore-backup) restore_backup="$2"; shift 2 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ -f "$STATE_DIR/current.json" && -f "$STATE_DIR/previous.json" ]] || die "current and previous release records are required"
current_class="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("migration_class") or "none")' "$STATE_DIR/current.json")"
previous_image="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["image"])' "$STATE_DIR/previous.json")"
previous_sha="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["commit"])' "$STATE_DIR/previous.json")"
current_sha="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["commit"])' "$STATE_DIR/current.json")"

if [[ "$current_class" == "breaking" && -z "$restore_backup" ]]; then
  backup_hint="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("backup") or "unknown")' "$STATE_DIR/current.json")"
  echo "restore_required previous=$previous_image current=$current_sha backup=$backup_hint" >&2
  die "breaking migration was applied; pass --restore-backup to restore the database before switching images"
fi

if [[ "$dry_run" -eq 1 ]]; then
  if [[ -n "$restore_backup" ]]; then
    echo "would_restore_then_switch image=$previous_image"
  else
    echo "would_switch image=$previous_image preserve_database=yes"
  fi
  exit 0
fi

require_cmd docker
"$HERE/check-env.sh" "$ENV_FILE"
load_env_file
if [[ -n "$restore_backup" ]]; then
  "$ROOT/scripts/restore/restore.sh" \
    --container pdoom-prod-postgres \
    --backup "$restore_backup" \
    --target-db "$POSTGRES_DB" \
    --confirm-replace \
    --confirm-production
fi

docker image inspect "$previous_image" >/dev/null
GIT_COMMIT="$previous_sha" BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)" PDOOM_WEB_IMAGE="$previous_image" \
  compose up -d --no-deps --force-recreate web
for _ in $(seq 1 40); do
  if docker exec pdoom-prod-web node -e "fetch('http://127.0.0.1:3000/api/ready').then((r)=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
[[ "${ready:-0}" -eq 1 ]] || die "previous image did not become ready"
docker tag "$previous_image" pdoom-live:current
python3 - "$STATE_DIR/current.json" "$STATE_DIR/previous.json" <<'PY'
import json, pathlib, sys
current = pathlib.Path(sys.argv[1])
previous = pathlib.Path(sys.argv[2])
old = json.loads(current.read_text())
new = json.loads(previous.read_text())
current.write_text(json.dumps(new, indent=2) + "\n")
previous.write_text(json.dumps(old, indent=2) + "\n")
PY
echo "rolled_back image=$previous_image database_restored=$([[ -n "$restore_backup" ]] && echo yes || echo no)"
