#!/usr/bin/env bash
# Exercise rollback state transitions with fake Docker; no daemon or DB needed.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/bin" "$WORK/backups"
cat >"$WORK/env" <<ENV
NODE_ENV=production
PDOOM_ENV=production
APP_BASE_URL=https://pdoom.live
PDOOM_WEB_IMAGE=pdoom-live:current
POSTGRES_USER=pdoom
POSTGRES_PASSWORD=rollback-routing-test-password
POSTGRES_DB=pdoom_live
DATABASE_URL=postgresql://pdoom:rollback-routing-test-password@postgres:5432/pdoom_live
ACME_EMAIL=ops@pdoom.live
PDOOM_BACKUP_DIR=$WORK/backups
ENV
chmod 600 "$WORK/env"
cat >"$WORK/bin/sleep" <<'SLEEP'
#!/usr/bin/env bash
exit 0
SLEEP
cat >"$WORK/bin/docker" <<'DOCKER'
#!/usr/bin/env bash
set -euo pipefail
state="$PDOOM_STATE_DIR"
event() { echo "$*" >>"$state/events"; }
target() { sed -n 's/^reverse_proxy \([^:]*\):3000.*/\1/p' "$state/upstream.caddy"; }
case "$1" in
  image)
    event image-check
    [[ "$TEST_MODE" != image-missing ]]
    ;;
  run)
    if [[ "$*" == *'--entrypoint sh'* ]]; then
      echo 001_init.sql
    else
      while [[ "$1" != --name ]]; do shift; done
      echo "$2" >"$state/candidate"
      event candidate
    fi
    ;;
  exec)
    if [[ "$*" == *'SELECT 1 FROM pg_database'* ]]; then
      echo 1
    elif [[ "$*" == *'dropdb'* || "$*" == *'createdb'* ]]; then
      event restore-database
    elif [[ "$*" == *'pg_restore'* ]]; then
      cat >/dev/null
      touch "$state/restored"
      event restore-load
    elif [[ "$*" == *'SELECT version'* ]]; then
      event migrations
      [[ "$TEST_MODE" != migration-query-fail ]] || exit 1
      echo 001_init.sql
      if [[ "$TEST_MODE" == migration-mismatch || ( "$TEST_MODE" == restored && ! -f "$state/restored" ) ]]; then
        echo 006_unrecorded_breaking.sql
      fi
    elif [[ "$*" == *'caddy reload'* ]]; then
      selected="$(target)"
      test -f "$state/mount-reconciled"
      [[ "$TEST_MODE" != proxy-initial-fail ]] || exit 1
      if [[ "$selected" == pdoom-prod-web-rollback-* ]]; then
        [[ "$TEST_MODE" != proxy-switch-fail ]] || exit 1
        event reload-candidate
      elif [[ -f "$state/web-recreated" ]]; then
        [[ "$TEST_MODE" != proxy-final-fail ]] || exit 1
        event reload-web
      else
        event reload-original
      fi
    elif [[ "$2" == pdoom-prod-web-rollback-* ]]; then
      [[ "$TEST_MODE" != candidate-fail ]] || exit 1
      event candidate-ready
    elif [[ "$2" == pdoom-prod-web ]]; then
      [[ "$TEST_MODE" != web-not-ready ]] || exit 1
      event web-ready
    else
      exit 1
    fi
    ;;
  compose)
    if [[ "${*: -1}" == caddy ]]; then
      event reconcile-proxy
      [[ "$TEST_MODE" != reconcile-fail ]] || exit 1
      touch "$state/mount-reconciled"
      exit 0
    fi
    [[ "$(target)" == pdoom-prod-web-rollback-* ]]
    event recreate-web
    touch "$state/web-recreated"
    [[ "$TEST_MODE" != web-create-fail ]]
    ;;
  rm)
    event remove
    printf '%s\n' "$*" >>"$state/removed"
    ;;
  tag) event tag ;;
  *) echo "unexpected fake docker command: $1" >&2; exit 1 ;;
esac
DOCKER
chmod +x "$WORK/bin/"*
for mode in normal stale-candidate restored image-missing migration-mismatch migration-query-fail candidate-fail reconcile-fail proxy-initial-fail proxy-switch-fail web-create-fail web-not-ready proxy-final-fail; do
  state="$WORK/$mode"
  mkdir -p "$state"
  : >"$state/events"
  printf '{"commit":"%040d","image":"pdoom-live:%040d","migration_class":"none"}\n' 1 1 >"$state/current.json"
  printf '{"commit":"%040d","image":"pdoom-live:%040d","migration_class":"none"}\n' 2 2 >"$state/previous.json"
  cp "$state/current.json" "$state/original-current.json"
  cp "$state/previous.json" "$state/original-previous.json"
  initial=web
  [[ "$mode" == normal ]] || initial=pdoom-prod-web-candidate
  sed "s|reverse_proxy web:3000|reverse_proxy $initial:3000|" "$ROOT/deploy/caddy/upstream.caddy" >"$state/upstream.caddy"
  cp "$state/upstream.caddy" "$state/original-upstream.caddy"
  args=()
  if [[ "$mode" == restored ]]; then
    # A verified scratch archive exercises the existing restore tool; Docker is fake.
    printf 'mock archive' >"$state/backup.dump"
    (cd "$state" && sha256sum backup.dump >backup.sha256)
    args=(--restore-backup "$state/backup.dump")
  fi
  set +e
  env PATH="$WORK/bin:$PATH" PDOOM_ROOT="$ROOT" PDOOM_STATE_DIR="$state" \
    PDOOM_ENV_FILE="$WORK/env" TEST_MODE="$mode" \
    bash "$ROOT/scripts/deploy/rollback.sh" "${args[@]}" >"$state/output" 2>&1
  result=$?
  set -e
  if [[ "$mode" == normal || "$mode" == stale-candidate || "$mode" == restored ]]; then
    [[ "$result" == 0 ]] || { cat "$state/output" >&2; exit 1; }
    grep -q '^rolled_back ' "$state/output"
    printf 'image-check\nmigrations\ncandidate\ncandidate-ready\nreconcile-proxy\nreload-original\nreload-candidate\nrecreate-web\nweb-ready\nreload-web\nremove\ntag\n' >"$state/expected"
    if [[ "$mode" == restored ]]; then
      sed -i '/image-check/a restore-database\nrestore-database\nrestore-load' "$state/expected"
      grep -q 'database_restored=yes' "$state/output"
    fi
    diff -u "$state/expected" "$state/events"
    python3 - "$state" <<'PY'
import json, pathlib, sys
p=pathlib.Path(sys.argv[1])
assert json.loads((p/'current.json').read_text()) == json.loads((p/'original-previous.json').read_text())
assert json.loads((p/'previous.json').read_text()) == json.loads((p/'original-current.json').read_text())
PY
    grep -q '^reverse_proxy web:3000' "$state/upstream.caddy"
    grep -q 'pdoom-prod-web-candidate' "$state/removed"
  else
    [[ "$result" != 0 ]] || { echo "unexpected success: $mode" >&2; exit 1; }
    ! grep -q '^rolled_back ' "$state/output"
    cmp "$state/current.json" "$state/original-current.json"
    cmp "$state/previous.json" "$state/original-previous.json"
    case "$mode" in
      image-missing|migration-mismatch|migration-query-fail)
        test ! -f "$state/candidate"
        cmp "$state/upstream.caddy" "$state/original-upstream.caddy"
        ;;
      candidate-fail|reconcile-fail|proxy-initial-fail|proxy-switch-fail)
        ! grep -q recreate-web "$state/events"
        cmp "$state/upstream.caddy" "$state/original-upstream.caddy"
        ;;
      web-create-fail|web-not-ready|proxy-final-fail)
        grep -q '^reverse_proxy pdoom-prod-web-rollback-' "$state/upstream.caddy"
        test ! -f "$state/removed"
        ;;
    esac
    if [[ "$mode" == migration-mismatch ]]; then
      grep -q 'restore a matching verified database backup' "$state/output"
    fi
  fi
  ! grep -q 'rollback-routing-test-password' "$state/output"
done
printf 'rollback_routing_test_ok\n'
