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
    echo "would_switch image=$previous_image verify_database_migrations=yes preserve_database_if_matching=yes"
  fi
  exit 0
fi

require_cmd docker
"$HERE/check-env.sh" "$ENV_FILE"
load_env_file
prepare_state
# Refuse a missing rollback image before changing any database or serving process.
docker image inspect "$previous_image" >/dev/null
if [[ -n "$restore_backup" ]]; then
  "$ROOT/scripts/restore/restore.sh" \
    --container pdoom-prod-postgres \
    --backup "$restore_backup" \
    --target-db "$POSTGRES_DB" \
    --confirm-replace \
    --confirm-production
fi

# Release records are written only after promotion, so a failed release may have
# committed migrations that current.json does not mention. Compare the actual DB
# to the selected image, even after an explicitly requested restore. Never infer
# safety from a stale "none"/"compatible" release class.
expected_migrations="$(docker run --rm --entrypoint sh "$previous_image" -c 'find /app/migrations -maxdepth 1 -type f -name "*.sql" -printf "%f\n" | sort')"
applied_migrations="$(docker exec -u postgres pdoom-prod-postgres psql --username "$POSTGRES_USER" -d "$POSTGRES_DB" --set ON_ERROR_STOP=1 -tAc "SELECT version FROM schema_migrations ORDER BY version" | sort)"
if [[ -z "$expected_migrations" || "$applied_migrations" != "$expected_migrations" ]]; then
  die "database migrations do not match the rollback image; restore a matching verified database backup with --restore-backup before switching images"
fi

wait_ready() {
  local name="$1" attempt
  for attempt in $(seq 1 40); do
    if docker exec "$name" node -e "fetch('http://127.0.0.1:3000/api/ready').then((r)=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

# Do not remove a candidate left serving by an earlier failed rollback. Each
# attempt gets its own name, and only retires it after a confirmed proxy switch.
candidate="pdoom-prod-web-rollback-${previous_sha:0:12}-$$"
original_upstream="$(mktemp)"
cp "$STATE_DIR/upstream.caddy" "$original_upstream"
trap 'rm -f "$original_upstream"' EXIT

docker run -d --name "$candidate" --network pdoom-prod \
  --restart unless-stopped --log-opt max-size=10m --log-opt max-file=3 \
  -e NODE_ENV=production -e PDOOM_ENV=production \
  -e APP_BASE_URL="$APP_BASE_URL" -e DATABASE_URL="$DATABASE_URL" \
  -e PORT=3000 -e HOSTNAME=0.0.0.0 -e PDOOM_MIGRATIONS_DIR=/app/migrations \
  "$previous_image" >/dev/null
if ! wait_ready "$candidate"; then
  docker rm -f "$candidate" >/dev/null 2>&1 || true
  die "rollback candidate did not become ready; existing routing and release records are unchanged"
fi

# A rollback may be the first operation after upgrading from the old single-file
# proxy mount. Reconcile it before trusting reloads; --no-deps keeps web untouched.
if ! compose up -d --no-deps caddy; then
  docker rm -f "$candidate" >/dev/null 2>&1 || true
  die "rollback proxy reconciliation failed; existing web and release records are unchanged"
fi
# Establish that the running proxy accepts its existing route before replacing
# the on-disk target. A missing/unready proxy cannot count as a successful switch.
if ! reload_caddy; then
  docker rm -f "$candidate" >/dev/null 2>&1 || true
  die "rollback proxy was not ready; existing routing and release records are unchanged"
fi
render_upstream "$candidate"
if ! reload_caddy; then
  # A transport failure is not proof that Caddy rejected the request. Restore the
  # previous config, try to load it, and keep the candidate alive in either case.
  cat "$original_upstream" >"$STATE_DIR/upstream.caddy.next"
  mv "$STATE_DIR/upstream.caddy.next" "$STATE_DIR/upstream.caddy"
  reload_caddy || true
  die "rollback proxy switch failed; original routing configuration restored, containers retained, release records unchanged"
fi

if ! GIT_COMMIT="$previous_sha" PDOOM_WEB_IMAGE="$previous_image" \
  compose up -d --no-deps --force-recreate web; then
  die "rollback web recreation failed; traffic remains on $candidate and release records are unchanged"
fi
if ! wait_ready pdoom-prod-web; then
  die "rollback web did not become ready; traffic remains on $candidate and release records are unchanged"
fi
render_upstream web
if ! reload_caddy; then
  render_upstream "$candidate"
  reload_caddy || true
  die "rollback final proxy switch failed; rollback candidate retained and release records are unchanged"
fi

# Only a confirmed final reload permits retiring fallback targets and recording
# success. This also clears the stale release candidate from a failed promotion.
docker rm -f "$candidate" pdoom-prod-web-candidate >/dev/null 2>&1 || true
docker tag "$previous_image" pdoom-live:current
python3 - "$STATE_DIR/current.json" "$STATE_DIR/previous.json" <<'PY_STATE'
import json, pathlib, sys
current = pathlib.Path(sys.argv[1])
previous = pathlib.Path(sys.argv[2])
old = json.loads(current.read_text())
new = json.loads(previous.read_text())
current.write_text(json.dumps(new, indent=2) + "\n")
previous.write_text(json.dumps(old, indent=2) + "\n")
PY_STATE
echo "rolled_back image=$previous_image database_restored=$([[ -n "$restore_backup" ]] && echo yes || echo no)"
