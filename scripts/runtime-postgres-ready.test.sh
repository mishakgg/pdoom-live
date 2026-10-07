#!/usr/bin/env bash
# Stop a fake runtime smoke at migration to test its real startup gate only.
# No Docker daemon, server, image or real database is used.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/bin"
cat >"$WORK/bin/docker" <<'DOCKER'
#!/usr/bin/env bash
set -euo pipefail
state="${READY_TEST_STATE:?}"
case "$1" in
  image) echo 305496785 ;;
  network|rm) exit 0 ;;
  run)
    if [[ "$*" == *'pdoom-cli.mjs migrate'* ]]; then
      touch "$state/migration-started"
      echo migration-reached
      exit 42
    fi
    ;;
  exec)
    [[ "$*" == *pg_isready* ]] || exit 1
    count="$(cat "$state/count" 2>/dev/null || echo 0)"
    count=$((count + 1))
    echo "$count" >"$state/count"
    # Demonstrate the bad witness: initdb's Unix socket answers immediately.
    # A regression to the old no-host probe would trust this temporary server.
    if [[ "$*" != *'-h 127.0.0.1'* || "$*" != *'-p 5432'* ]]; then
      touch "$state/socket-probe"
      exit 0
    fi
    [[ "$*" == *'-t 2'* ]] || { echo missing-probe-timeout >&2; exit 1; }
    mode="$(cat "$state/mode")"
    if [[ "$mode" == immediate || ( "$mode" == delayed && "$count" -ge 3 ) ]]; then
      exit 0
    fi
    echo 'private-probe-detail-must-not-leak' >&2
    exit 1
    ;;
  inspect)
    if [[ "$(cat "$state/mode")" == unknown-state ]]; then
      echo private-container-detail-must-not-leak
    else
      echo running
    fi
    ;;
  *) echo unexpected-fake-docker-command >&2; exit 1 ;;
esac
DOCKER
cat >"$WORK/bin/sleep" <<'SLEEP'
#!/usr/bin/env bash
exit 0
SLEEP
chmod +x "$WORK/bin/"*
for mode in immediate delayed never unknown-state; do
  state="$WORK/$mode"
  mkdir -p "$state"
  echo "$mode" >"$state/mode"
  set +e
  READY_TEST_STATE="$state" PATH="$WORK/bin:$PATH" bash "$ROOT/scripts/runtime-smoke.sh" pdoom-live:ci >"$state/output" 2>&1
  result=$?
  set -e
  test ! -f "$state/socket-probe"
  ! grep -q 'private-' "$state/output"
  case "$mode" in
    immediate|delayed)
      [[ "$result" == 42 ]]
      test -f "$state/migration-started"
      grep -q migration-reached "$state/output"
      if [[ "$mode" == immediate ]]; then
        [[ "$(cat "$state/count")" == 1 ]]
      else
        [[ "$(cat "$state/count")" == 3 ]]
      fi
      ;;
    never|unknown-state)
      [[ "$result" == 1 ]]
      test ! -f "$state/migration-started"
      [[ "$(cat "$state/count")" == 40 ]]
      grep -q 'TCP readiness timed out after 40 attempts' "$state/output"
      if [[ "$mode" == never ]]; then
        grep -q 'container_state=running' "$state/output"
      else
        grep -q 'container_state=unknown' "$state/output"
      fi
      ;;
  esac
done
printf 'runtime_postgres_ready_test_ok\n'
