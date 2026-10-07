#!/usr/bin/env bash
# Measure user-visible downtime while Caddy reloads onto an already-ready upstream.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
command -v docker >/dev/null
command -v curl >/dev/null

NET="pdoom-switch-$$"
A="pdoom-a-$$"
B="pdoom-b-$$"
CADDY="pdoom-switch-caddy-$$"
WORK="$(mktemp -d)"
PORT="${PDOOM_SWITCH_PORT:-18081}"
cleanup() {
  docker rm -f "$A" "$B" "$CADDY" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
  rm -rf "$WORK"
}
trap cleanup EXIT

# Use the same atomic writer and directory mount as the production release.
source "$ROOT/scripts/deploy/lib.sh"
STATE_DIR="$WORK/state"
mkdir -p "$STATE_DIR"
cat >"$WORK/Caddyfile" <<'EOF'
{
	auto_https off
	admin localhost:2019
}
:80 {
	import /etc/caddy/state/upstream.caddy
}
EOF

printf 'ready\n' >"$WORK/mode"
render_upstream mock-a
docker network create "$NET" >/dev/null
docker run -d --name "$A" --network "$NET" --network-alias mock-a \
  -e MODE_FILE=/mode/mode -e BODY=from-a \
  -v "$WORK:/mode" -v "$ROOT/scripts/deploy/ready-mock.mjs:/ready-mock.mjs:ro" \
  node:22-bookworm-slim node /ready-mock.mjs >/dev/null
docker run -d --name "$B" --network "$NET" --network-alias mock-b \
  -e MODE_FILE=/mode/mode -e BODY=from-b \
  -v "$WORK:/mode" -v "$ROOT/scripts/deploy/ready-mock.mjs:/ready-mock.mjs:ro" \
  node:22-bookworm-slim node /ready-mock.mjs >/dev/null
docker run -d --name "$CADDY" --network "$NET" -p "127.0.0.1:${PORT}:80" \
  -v "$WORK:/etc/caddy:ro" \
  caddy:2.10-alpine >/dev/null

for _ in $(seq 1 30); do
  if curl -fsS --max-time 2 "http://127.0.0.1:${PORT}/" | grep -q from-a; then
    break
  fi
  sleep 0.2
done

samples="$WORK/samples"
: >"$samples"
stop="$WORK/stop"
(
  while [[ ! -f "$stop" ]]; do
    now="$(date +%s%3N)"
    if body="$(curl -fsS --max-time 2 "http://127.0.0.1:${PORT}/" 2>/dev/null)"; then
      printf '%s ok %s\n' "$now" "$body" >>"$samples"
    else
      printf '%s fail\n' "$now" >>"$samples"
    fi
  done
) &
loop=$!
sleep 0.4
switch_at="$(date +%s%3N)"
render_upstream mock-b
docker exec "$CADDY" caddy reload --config /etc/caddy/Caddyfile --adapter caddyfile
for _ in $(seq 1 30); do
  if curl -fsS --max-time 2 "http://127.0.0.1:${PORT}/" | grep -q from-b; then
    break
  fi
  sleep 0.1
done
# A reload is insufficient evidence: remove the old upstream and require the
# proxy to keep serving the candidate through the same directory bind mount.
docker rm -f "$A" >/dev/null
curl -fsS --max-time 2 "http://127.0.0.1:${PORT}/" | grep -q from-b
sleep 0.4
touch "$stop"
wait "$loop" || true

python3 - "$samples" "$switch_at" <<'PY'
import sys
samples = []
for line in open(sys.argv[1], encoding="utf-8"):
    parts = line.split()
    if len(parts) < 2:
        continue
    samples.append((int(parts[0]), parts[1], parts[2] if len(parts) > 2 else ""))
switch_at = int(sys.argv[2])
failures = [item for item in samples if item[1] != "ok"]
oks = [item for item in samples if item[1] == "ok"]
outage = 0
for previous, current in zip(samples, samples[1:]):
    if previous[1] == "ok" and current[1] != "ok":
        nxt = next((item[0] for item in samples if item[0] > current[0] and item[1] == "ok"), None)
        if nxt is not None:
            outage = max(outage, nxt - previous[0])
saw_b = any(item[2] == "from-b" for item in samples)
print(f"switch_samples={len(samples)}")
print(f"switch_failures={len(failures)}")
print(f"user_visible_outage_ms={outage}")
print(f"saw_new_upstream={str(saw_b).lower()}")
print(f"switch_started_ms={switch_at}")
if not saw_b or not samples:
    sys.exit("switch did not reach the new upstream")
PY
