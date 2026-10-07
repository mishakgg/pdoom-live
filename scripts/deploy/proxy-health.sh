#!/usr/bin/env bash
# Validate the production Caddyfile and exercise upstream health behavior without ACME.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
require() { command -v "$1" >/dev/null || { echo "missing $1" >&2; exit 1; }; }
require docker
require curl

NET="pdoom-proxy-$$"
MOCK="pdoom-mock-$$"
CADDY="pdoom-caddy-$$"
WORK="$(mktemp -d)"
PORT="${PDOOM_PROXY_TEST_PORT:-18080}"
cleanup() {
  docker rm -f "$MOCK" "$CADDY" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

docker run --rm \
  -e ACME_EMAIL=ops@pdoom.live \
  -v "$ROOT/deploy/caddy/Caddyfile:/etc/caddy/Caddyfile:ro" \
  -v "$ROOT/deploy/caddy:/etc/caddy/state:ro" \
  caddy:2.10-alpine \
  caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

cat >"$WORK/Caddyfile" <<'EOF'
{
	admin off
	auto_https off
}
:80 {
	reverse_proxy mock:3000 {
		health_uri /api/ready
		health_interval 1s
		health_timeout 1s
		health_status 200
		fail_duration 1s
		max_fails 1
		unhealthy_status 503
		lb_retries 0
		lb_try_duration 1s
	}
}
EOF
printf 'ready\n' >"$WORK/mode"
docker network create "$NET" >/dev/null
docker run -d --name "$MOCK" --network "$NET" --network-alias mock \
  -e MODE_FILE=/mode/mode \
  -e BODY=ok \
  -v "$WORK:/mode" \
  -v "$ROOT/scripts/deploy/ready-mock.mjs:/ready-mock.mjs:ro" \
  node:22-bookworm-slim node /ready-mock.mjs >/dev/null
docker run -d --name "$CADDY" --network "$NET" -p "127.0.0.1:${PORT}:80" \
  -v "$WORK/Caddyfile:/etc/caddy/Caddyfile:ro" \
  caddy:2.10-alpine >/dev/null

fetch() {
  curl -sS -o "$WORK/body" -w '%{http_code}' --max-time 4 "http://127.0.0.1:${PORT}/" || echo 000
}

expect() {
  local want="$1" needle="${2:-}" i code
  for i in $(seq 1 12); do
    code="$(fetch)"
    if [[ "$code" == "$want" ]]; then
      if [[ -z "$needle" ]] || grep -q "$needle" "$WORK/body"; then
        return 0
      fi
    fi
    sleep 1
  done
  echo "expected HTTP $want, last code $code, body=$(cat "$WORK/body" 2>/dev/null || true)" >&2
  exit 1
}

expect_unready() {
  local i code
  for i in $(seq 1 15); do
    code="$(fetch)"
    if [[ "$code" == "503" ]] && ! grep -q 'app-not-ready' "$WORK/body"; then
      return 0
    fi
    sleep 1
  done
  echo "caddy still proxied an unready upstream, code=$code body=$(cat "$WORK/body" 2>/dev/null || true)" >&2
  exit 1
}

expect 200 ok
printf 'db-down\n' >"$WORK/mode"
expect_unready
printf 'migration\n' >"$WORK/mode"
expect_unready
printf 'starting\n' >"$WORK/mode"
expect_unready
printf 'ready\n' >"$WORK/mode"
expect 200 ok
docker rm -f "$MOCK" >/dev/null
start="$(date +%s)"
code="$(fetch)"
elapsed="$(( $(date +%s) - start ))"
if [[ "$elapsed" -gt 5 ]]; then
  echo "unavailable upstream took ${elapsed}s" >&2
  exit 1
fi
if [[ "$code" == "200" ]]; then
  echo "stopped upstream still returned 200" >&2
  exit 1
fi
echo "proxy_health_ok unavailable_code=$code unavailable_seconds=$elapsed"
