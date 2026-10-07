#!/usr/bin/env bash
# Exercise release ordering with fake Docker/Git; never touches a Docker daemon.
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
POSTGRES_PASSWORD=release-switch-test-password
POSTGRES_DB=pdoom_live
DATABASE_URL=postgresql://pdoom:release-switch-test-password@postgres:5432/pdoom_live
ACME_EMAIL=ops@pdoom.live
PDOOM_BACKUP_DIR=$WORK/backups
PDOOM_MIN_FREE_MB=0
ENV
chmod 600 "$WORK/env"
cat >"$WORK/bin/git" <<'GIT'
#!/usr/bin/env bash
case "$*" in
  *'status --porcelain'*) exit 0 ;;
  *'rev-parse HEAD'*) printf '%040d\n' 1 ;;
  *) exit 1 ;;
esac
GIT
cat >"$WORK/bin/docker" <<'DOCKER'
#!/usr/bin/env bash
set -euo pipefail
case "$1" in
  build|tag|rm|image|images|logs|system|volume) exit 0 ;;
  compose)
    case "${*: -1}" in
      postgres) exit 0 ;;
      caddy)
        printf 'reconcile\n' >>"$TEST_EVENTS"
        grep -q 'reverse_proxy web:3000' "$PDOOM_STATE_DIR/upstream.caddy"
        [[ "$TEST_MODE" != fail-proxy ]]
        ;;
      web)
        printf 'recreate\n' >>"$TEST_EVENTS"
        grep -q 'reverse_proxy pdoom-prod-web-candidate:3000' "$PDOOM_STATE_DIR/upstream.caddy"
        ;;
      *) exit 1 ;;
    esac
    ;;
  run)
    if [[ "$*" == *'--entrypoint sh'* ]]; then
      find "$PDOOM_ROOT/packages/db/migrations" -name '*.sql' -printf '%f\n' | sort
    else
      printf 'candidate\n' >>"$TEST_EVENTS"
    fi
    ;;
  ps) printf 'pdoom-prod-web\npdoom-prod-caddy\n' ;;
  inspect) echo true ;;
  exec)
    if [[ "$*" == *'SELECT version'* ]]; then
      find "$PDOOM_ROOT/packages/db/migrations" -name '*.sql' -printf '%f\n' | sort
    elif [[ "$*" == *'caddy reload'* ]]; then
      count_file="$PDOOM_STATE_DIR/reload-count"
      count="$(cat "$count_file" 2>/dev/null || echo 0)"
      count=$((count + 1))
      echo "$count" >"$count_file"
      [[ "$TEST_MODE" != never-ready ]] || exit 1
      [[ "$TEST_MODE" != slow-proxy || "$count" -gt 2 ]] || exit 1
      if grep -q 'reverse_proxy pdoom-prod-web-candidate:3000' "$PDOOM_STATE_DIR/upstream.caddy"; then
        echo reload-candidate >>"$TEST_EVENTS"
      else
        echo reload-web >>"$TEST_EVENTS"
      fi
    fi
    ;;
  *) printf 'unexpected fake docker command\n' >&2; exit 1 ;;
esac
DOCKER
cat >"$WORK/bin/sleep" <<'SLEEP'
#!/usr/bin/env bash
exit 0
SLEEP
chmod +x "$WORK/bin/git" "$WORK/bin/docker" "$WORK/bin/sleep"
for mode in success slow-proxy never-ready fail-proxy; do
  state="$WORK/$mode"
  mkdir -p "$state"
  : >"$state/events"
  cp "$ROOT/deploy/caddy/upstream.caddy" "$state/upstream.caddy"
  set +e
  env PATH="$WORK/bin:$PATH" PDOOM_ROOT="$ROOT" PDOOM_STATE_DIR="$state" \
    PDOOM_ENV_FILE="$WORK/env" TEST_EVENTS="$state/events" TEST_MODE="$mode" \
    bash "$ROOT/scripts/deploy/release.sh" >"$state/output" 2>&1
  result=$?
  set -e
  if [[ "$mode" == success || "$mode" == slow-proxy ]]; then
    [[ "$result" == 0 ]] || { cat "$state/output" >&2; exit 1; }
    printf 'candidate\nreconcile\nreload-web\nreload-candidate\nrecreate\nreload-web\n' >"$state/expected"
    diff -u "$state/expected" "$state/events"
    test -f "$state/current.json"
    if [[ "$mode" == slow-proxy ]]; then
      [[ "$(cat "$state/reload-count")" == 5 ]] || exit 1
    fi
    grep -q 'reverse_proxy web:3000' "$state/upstream.caddy"
  else
    [[ "$result" != 0 ]] || exit 1
    printf 'candidate\nreconcile\n' >"$state/expected"
    diff -u "$state/expected" "$state/events"
    test ! -f "$state/current.json"
    if [[ "$mode" == never-ready ]]; then
      [[ "$(cat "$state/reload-count")" == 40 ]] || exit 1
      grep -q 'Caddy did not accept its configuration' "$state/output"
    fi
    grep -q 'reverse_proxy web:3000' "$state/upstream.caddy"
  fi
done
printf 'release_switch_test_ok\n'
