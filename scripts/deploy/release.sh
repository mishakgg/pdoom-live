#!/usr/bin/env bash
# Build a commit-tagged image, migrate, wait for readiness, then promote it.
# Dataset import is a separate command: scripts/deploy/publish-dataset.sh
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=lib.sh
source "$HERE/lib.sh"
require_cmd docker git python3 sha256sum

ack=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ack-breaking) ack=1; shift ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ -z "$(git -C "$ROOT" status --porcelain)" ]] || die "working tree is not clean"
sha="$(git -C "$ROOT" rev-parse HEAD)"
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || die "commit SHA is invalid"
"$HERE/check-env.sh" "$ENV_FILE"
load_env_file
prepare_state
PDOOM_BACKUP_DIR="$PDOOM_BACKUP_DIR" PDOOM_MIN_FREE_MB="${PDOOM_MIN_FREE_MB:-1024}" "$HERE/disk.sh"

built_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "building pdoom-live:$sha"
docker build \
  --build-arg "GIT_COMMIT=$sha" \
  --build-arg "BUILD_TIME=$built_at" \
  -t "pdoom-live:$sha" \
  "$ROOT"
docker tag "pdoom-live:$sha" pdoom-live:candidate

compose up -d postgres
for _ in $(seq 1 40); do
  if docker exec pdoom-prod-postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker exec pdoom-prod-postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null

applied="$(mktemp)"
migration_dir="$(mktemp -d)"
trap 'rm -rf "$applied" "$migration_dir"' EXIT
docker exec -u postgres pdoom-prod-postgres psql --username "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT version FROM schema_migrations ORDER BY version" >"$applied" 2>/dev/null || true
docker run --rm --entrypoint sh "pdoom-live:$sha" -c 'ls -1 /app/migrations' >"$migration_dir/names"
mkdir -p "$migration_dir/sql"
while IFS= read -r name; do
  [[ -z "$name" ]] && continue
  : >"$migration_dir/sql/$name"
done <"$migration_dir/names"
class_json="$(classify_migrations "$migration_dir/sql" "$applied" "$CLASS_FILE")"
class="$(python3 -c 'import json,sys; print(json.loads(sys.argv[1])["class"])' "$class_json")"
pending="$(python3 -c 'import json,sys; print(",".join(json.loads(sys.argv[1])["pending"]))' "$class_json")"
echo "migration_class=$class pending=${pending:-none}"
if [[ "$class" == "diverged" ]]; then
  die "database has migrations this release does not contain; refusing to promote"
fi
backup_path=""
if [[ "$class" == "breaking" && "$ack" -ne 1 ]]; then
  die "pending migration is breaking; rerun with --ack-breaking so a backup is taken before it is applied"
fi
if [[ "$class" == "breaking" || "$class" == "compatible" ]]; then
  backup_path="$(PDOOM_PG_CONTAINER=pdoom-prod-postgres POSTGRES_DB="$POSTGRES_DB" PDOOM_BACKUP_DIR="$PDOOM_BACKUP_DIR" PDOOM_APP_COMMIT="$sha" "$ROOT/scripts/backup/backup.sh")"
  echo "pre_migration_backup=$backup_path"
  if ! docker run --rm --network pdoom-prod \
    -e NODE_ENV=production \
    -e PDOOM_ENV=production \
    -e APP_BASE_URL="$APP_BASE_URL" \
    -e DATABASE_URL="$DATABASE_URL" \
    -e PDOOM_MIGRATIONS_DIR=/app/migrations \
    "pdoom-live:$sha" \
    node /app/pdoom-cli.mjs migrate; then
    die "migration failed and was rolled back; the previous web container was left in place"
  fi
fi

run_web() {
  local name="$1"
  docker rm -f "$name" >/dev/null 2>&1 || true
  docker run -d --name "$name" --network pdoom-prod \
    --log-opt max-size=10m --log-opt max-file=3 \
    -e NODE_ENV=production \
    -e PDOOM_ENV=production \
    -e APP_BASE_URL="$APP_BASE_URL" \
    -e DATABASE_URL="$DATABASE_URL" \
    -e PORT=3000 \
    -e HOSTNAME=0.0.0.0 \
    -e PDOOM_MIGRATIONS_DIR=/app/migrations \
    -e GIT_COMMIT="$sha" \
    -e BUILD_TIME="$built_at" \
    "pdoom-live:$sha" >/dev/null
}

wait_ready() {
  local name="$1" i
  for i in $(seq 1 40); do
    if ! docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null | grep -qx true; then
      docker logs "$name" >&2 || true
      return 1
    fi
    if docker exec "$name" node -e "fetch('http://127.0.0.1:3000/api/ready').then((r)=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  docker logs "$name" >&2 || true
  return 1
}

abort_candidate() {
  docker rm -f pdoom-prod-web-candidate >/dev/null 2>&1 || true
  if [[ "$class" == "breaking" ]]; then
    echo "breaking migrations were applied; rolling back the web image is unsafe until backup ${backup_path:-unknown} is restored" >&2
  fi
  die "candidate did not become ready; it was not promoted"
}

if docker ps --format '{{.Names}}' | grep -qx pdoom-prod-web; then
  run_web pdoom-prod-web-candidate
  if ! wait_ready pdoom-prod-web-candidate; then
    abort_candidate
  fi
  # Reconcile changed proxy mounts before replacing the upstream file. The
  # migration from a single-file mount requires one Caddy recreation; subsequent
  # releases keep the running proxy. --no-deps leaves the serving web untouched.
  compose up -d --no-deps caddy
  # Confirm the current route works at the admin boundary before changing its
  # on-disk target. A cold-start failure leaves the old web and routing intact.
  reload_caddy
  render_upstream pdoom-prod-web-candidate
  reload_caddy
  GIT_COMMIT="$sha" BUILD_TIME="$built_at" PDOOM_WEB_IMAGE="pdoom-live:$sha" compose up -d --no-deps --force-recreate web
  if ! wait_ready pdoom-prod-web; then
    render_upstream pdoom-prod-web-candidate
    reload_caddy
    echo "promoted container did not become ready; traffic remains on the candidate and this release was not recorded" >&2
    if [[ "$class" == "breaking" ]]; then
      echo "breaking migrations were applied; rolling back the web image is unsafe until backup ${backup_path:-unknown} is restored" >&2
    fi
    die "candidate stayed up; the new web container was not promoted"
  fi
  render_upstream web
  reload_caddy
  docker rm -f pdoom-prod-web-candidate >/dev/null 2>&1 || true
else
  GIT_COMMIT="$sha" BUILD_TIME="$built_at" PDOOM_WEB_IMAGE="pdoom-live:$sha" compose up -d --no-deps web
  if ! wait_ready pdoom-prod-web; then
    docker rm -f pdoom-prod-web >/dev/null 2>&1 || true
    die "web container did not become ready; it was removed and was not promoted"
  fi
  render_upstream web
  compose up -d caddy
fi

docker tag "pdoom-live:$sha" pdoom-live:current
if [[ -f "$STATE_DIR/current.json" ]]; then
  cp "$STATE_DIR/current.json" "$STATE_DIR/previous.json"
  previous_sha="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("commit") or "")' "$STATE_DIR/previous.json")"
  if [[ -n "$previous_sha" ]]; then
    docker tag "pdoom-live:$previous_sha" pdoom-live:previous 2>/dev/null || true
  fi
fi
python3 - "$STATE_DIR/current.json" "$sha" "$built_at" "$class" "$backup_path" <<'PY'
import json, sys
path, sha, built_at, kind, backup = sys.argv[1:]
payload = {
    "commit": sha,
    "image": f"pdoom-live:{sha}",
    "built_at": built_at,
    "migration_class": kind,
    "backup": backup or None,
    "promoted_at": built_at,
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle, indent=2)
    handle.write("\n")
PY

mapfile -t remove_tags < <(docker images pdoom-live --format '{{.Tag}}' | images_to_remove "$sha" "${previous_sha:-}")
for tag in "${remove_tags[@]:-}"; do
  [[ -z "$tag" ]] && continue
  docker image rm "pdoom-live:$tag" >/dev/null || true
done

if ! wait_ready pdoom-prod-web; then
  die "promoted web container is not ready"
fi
echo "promoted pdoom-live:$sha"
