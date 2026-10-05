#!/usr/bin/env bash
# The restore drill used to stop at the first local pg_isready success.
# That success happens on Postgres' temporary init server, and the next check
# can exit 1 with its status on stdout. This test reproduces that sequence
# with a fake docker and does not need a daemon.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ready="$ROOT/scripts/restore/postgres-ready.sh"
fail() { printf 'postgres-ready test failed: %s\n' "$*" >&2; exit 1; }

assert_fail() {
  local expected="$1"
  shift
  local out code
  set +e
  out="$("$@" 2>&1)"
  code=$?
  set -e
  [[ "$code" -ne 0 ]] || fail "expected non-zero: $*"
  [[ "$out" == *"$expected"* ]] || fail "missing [$expected] in [$out]"
  [[ "$out" != *"drill-password-value"* ]] || fail "output included the drill password"
}

assert_fail "usage: postgres-ready.sh CONTAINER USER DATABASE" \
  env PATH="/usr/bin:/bin" bash "$ready"
assert_fail "container name is invalid" \
  env PATH="/usr/bin:/bin" bash "$ready" "bad name" pdoom pdoom_ops_drill
assert_fail "database name is invalid" \
  env PATH="/usr/bin:/bin" bash "$ready" pdoom-drill-pg-1 pdoom "bad-name"
assert_fail "database user is invalid" \
  env PATH="/usr/bin:/bin" bash "$ready" pdoom-drill-pg-1 "bad-user" pdoom_ops_drill

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
cat >"$work/docker" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
state="${READY_TEST_STATE:?}"
printf '%s\n' "$1" >>"$state/calls"
if [[ "$1" == "logs" ]]; then
  mode="$(cat "$state/mode")"
  count="$(grep -c '^logs$' "$state/calls" || true)"
  # Present in the captured log text. The waiter must not reprint it.
  printf '%s\n' "POSTGRES_PASSWORD=drill-password-value"
  if [[ "$mode" == "never" || ( "$mode" == "delay-marker" && "$count" -lt 3 ) ]]; then
    printf '%s\n' "database system is ready to accept connections"
    exit 0
  fi
  printf '%s\n' "PostgreSQL init process complete; ready for start up."
  printf '%s\n' "database system is ready to accept connections"
  touch "$state/marker_seen"
  exit 0
fi
if [[ "$1" == "exec" ]]; then
  if [[ ! -f "$state/marker_seen" ]]; then
    printf 'early\n' >>"$state/violations"
    exit 1
  fi
  printf 'exec\n' >>"$state/execs"
  mode="$(cat "$state/mode")"
  seen="$(grep -c '^exec$' "$state/execs" || true)"
  if [[ "$mode" == "retry-exec" && "$seen" -lt 2 ]]; then
    exit 1
  fi
  exit 0
fi
printf 'unexpected docker command\n' >&2
exit 1
EOF
chmod +x "$work/docker"

run_ready() {
  local mode="$1"
  local state="$work/$mode"
  mkdir -p "$state"
  printf '%s\n' "$mode" >"$state/mode"
  : >"$state/calls"
  env \
    PATH="$work:/usr/bin:/bin" \
    READY_TEST_STATE="$state" \
    PDOOM_POSTGRES_READY_ATTEMPTS=6 \
    PDOOM_POSTGRES_READY_INTERVAL=0 \
    bash "$ready" pdoom-drill-pg-12345 pdoom pdoom_ops_drill
}

out="$(run_ready delay-marker 2>&1)"
[[ -z "$out" ]] || fail "delay-marker printed [$out]"
[[ ! -f "$work/delay-marker/violations" ]] || fail "pg_isready ran before init finished"
[[ "$(grep -c '^exec$' "$work/delay-marker/execs")" == "1" ]] || fail "expected one ready check after init"
logs_before="$(grep -c '^logs$' "$work/delay-marker/calls")"
[[ "$logs_before" -ge 3 ]] || fail "returned before the temporary server restarted"

out="$(run_ready retry-exec 2>&1)"
[[ -z "$out" ]] || fail "retry-exec printed [$out]"
[[ "$(grep -c '^exec$' "$work/retry-exec/execs")" == "2" ]] || fail "did not retry pg_isready after init"

give_up="$work/give-up"
mkdir -p "$give_up"
printf '%s\n' "never" >"$give_up/mode"
: >"$give_up/calls"
set +e
out="$(env \
  PATH="$work:/usr/bin:/bin" \
  READY_TEST_STATE="$give_up" \
  PDOOM_POSTGRES_READY_ATTEMPTS=2 \
  PDOOM_POSTGRES_READY_INTERVAL=0 \
  bash "$ready" pdoom-drill-pg-12345 pdoom pdoom_ops_drill 2>&1)"
code=$?
set -e
[[ "$code" -ne 0 ]] || fail "gave up with status 0"
[[ "$out" == *"postgres did not become ready after its init server restarted"* ]] || fail "missing give-up message in [$out]"
[[ "$out" != *"drill-password-value"* ]] || fail "give-up output included the drill password"
[[ ! -f "$give_up/violations" ]] || fail "gave up after trusting an early pg_isready"

printf 'postgres_ready_test_ok\n'
