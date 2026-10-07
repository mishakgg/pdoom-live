#!/usr/bin/env bash
# Shared helpers for production deploy, backup, and restore scripts.
set -euo pipefail

ops_root() {
  local here
  here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  cd "$here/../.." && pwd
}

ROOT="${PDOOM_ROOT:-$(ops_root)}"
ENV_FILE="${PDOOM_ENV_FILE:-/etc/pdoom/production.env}"
STATE_DIR="${PDOOM_STATE_DIR:-$ROOT/deploy/state}"
CLASS_FILE="${PDOOM_MIGRATION_CLASS_FILE:-$ROOT/deploy/migration-class.tsv}"
COMPOSE_FILE="${PDOOM_COMPOSE_FILE:-$ROOT/compose.production.yaml}"

die() {
  echo "$*" >&2
  exit 1
}

require_cmd() {
  local cmd
  for cmd in "$@"; do
    command -v "$cmd" >/dev/null 2>&1 || die "required command is not installed: $cmd"
  done
}

valid_db_name() {
  [[ "$1" =~ ^[A-Za-z][A-Za-z0-9_]{0,62}$ ]]
}

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

prepare_state() {
  mkdir -p "$STATE_DIR"
  if [[ ! -f "$STATE_DIR/upstream.caddy" ]]; then
    cp "$ROOT/deploy/caddy/upstream.caddy" "$STATE_DIR/upstream.caddy"
  fi
}

# Directory bind mounts follow the renamed entry; a single-file mount would
# retain the old inode. Keep the write atomic so Caddy never reads a partial file.
render_upstream() {
  local host="$1"
  [[ "$host" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || die "upstream host is invalid"
  sed "s|reverse_proxy [^ ]*|reverse_proxy ${host}:3000|" "$ROOT/deploy/caddy/upstream.caddy" >"$STATE_DIR/upstream.caddy.next"
  mv "$STATE_DIR/upstream.caddy.next" "$STATE_DIR/upstream.caddy"
}

reload_caddy() {
  local attempt
  # Compose -d only starts the process. The admin listener may not be ready yet,
  # and an exited/restarting proxy must never turn a reload into a silent success.
  for attempt in $(seq 1 40); do
    if docker exec pdoom-prod-caddy caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "Caddy did not accept its configuration within 40 attempts; refusing to continue the traffic switch" >&2
  return 1
}

load_env_file() {
  [[ -f "$ENV_FILE" ]] || die "missing env file $ENV_FILE"
  local line key value
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%%$'\r'}"
    [[ -z "$line" || "$line" == \#* ]] && continue
    [[ "$line" == *'$'* || "$line" == *'`'* ]] && die "env file must contain KEY=VALUE lines without shell expansion"
    key="${line%%=*}"
    value="${line#*=}"
    [[ "$key" =~ ^[A-Z][A-Z0-9_]*$ ]] || die "env file has an invalid key"
    printf -v "$key" '%s' "$value"
    export "$key"
  done <"$ENV_FILE"
}

classify_migrations() {
  local migrations_dir="$1" applied_file="$2" class_file="$3"
  python3 - "$migrations_dir" "$applied_file" "$class_file" <<'PY'
import json, sys
from pathlib import Path
migrations = sorted(p.name for p in Path(sys.argv[1]).glob("*.sql"))
applied = [line.strip() for line in Path(sys.argv[2]).read_text().splitlines() if line.strip()]
classes = {}
for raw in Path(sys.argv[3]).read_text().splitlines():
    line = raw.split("#", 1)[0].strip()
    if not line:
        continue
    version, _, kind = line.partition("\t")
    if not version or kind not in {"compatible", "breaking"}:
        sys.exit(f"invalid migration class line: {raw}")
    classes[version] = kind
extra = sorted(set(applied) - set(migrations))
pending = [name for name in migrations if name not in set(applied)]
if extra:
    kind = "diverged"
elif not pending:
    kind = "none"
elif any(classes.get(name, "breaking") == "breaking" for name in pending):
    kind = "breaking"
else:
    kind = "compatible"
print(json.dumps({
    "class": kind,
    "pending": pending,
    "extra": extra,
    "ack_required": kind == "breaking",
}))
PY
}

images_to_remove() {
  local current="$1" previous="$2" tag
  while IFS= read -r tag; do
    [[ -z "$tag" ]] && continue
    case "$tag" in
      "$current"|"$previous"|current|previous|candidate|ci) continue ;;
    esac
    if [[ "$tag" =~ ^[0-9a-f]{7,40}$ ]]; then
      printf '%s\n' "$tag"
    fi
  done
}
