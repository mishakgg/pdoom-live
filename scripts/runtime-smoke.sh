#!/usr/bin/env bash
# Build, if needed, and smoke-test the production image against a throwaway database.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
IMAGE="${1:-pdoom-live:ci}"
NET="pdoom-smoke-$$"
PG="pdoom-pg-$$"
WEB="pdoom-web-$$"

cleanup() {
  docker rm -f "$WEB" "$PG" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
}
trap cleanup EXIT

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  docker build -t "$IMAGE" "$ROOT"
fi

echo "image_bytes=$(docker image inspect "$IMAGE" --format '{{.Size}}')"

docker network create "$NET" >/dev/null
docker run -d --name "$PG" --network "$NET" \
  -e POSTGRES_USER=pdoom \
  -e POSTGRES_PASSWORD=pdoom \
  -e POSTGRES_DB=pdoom_live \
  postgres:16 >/dev/null

for _ in $(seq 1 40); do
  if docker exec "$PG" pg_isready -U pdoom -d pdoom_live >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
docker exec "$PG" pg_isready -U pdoom -d pdoom_live >/dev/null

run_cli() {
  docker run --rm --network "$NET" \
    -e NODE_ENV=production \
    -e PDOOM_ENV=production \
    -e APP_BASE_URL=http://127.0.0.1:3000 \
    -e DATABASE_URL=postgresql://pdoom:pdoom@${PG}:5432/pdoom_live \
    -e PDOOM_MIGRATIONS_DIR=/app/migrations \
    "$IMAGE" \
    node /app/pdoom-cli.mjs "$@"
}

run_cli migrate

set +e
seed_logs="$(run_cli seed 2>&1)"
seed_code=$?
set -e
if [[ "$seed_code" -eq 0 ]]; then
  echo "production seed was allowed" >&2
  exit 1
fi
if [[ "$seed_logs" != *"refusing to seed"* ]]; then
  echo "$seed_logs" >&2
  echo "production seed failed for an unexpected reason" >&2
  exit 1
fi
if [[ "$seed_logs" == *"postgresql://"* || "$seed_logs" == *"postgres://"* ]]; then
  echo "seed error included a database URL" >&2
  exit 1
fi

if [[ -f "$ROOT/data/fixtures/synthetic/dataset.json" ]]; then
  set +e
  import_logs="$(docker run --rm --network "$NET" \
    -e NODE_ENV=production \
    -e PDOOM_ENV=production \
    -e APP_BASE_URL=http://127.0.0.1:3000 \
    -e DATABASE_URL=postgresql://pdoom:pdoom@${PG}:5432/pdoom_live \
    -e PDOOM_MIGRATIONS_DIR=/app/migrations \
    -v "$ROOT/data/fixtures/synthetic/dataset.json:/dataset.json:ro" \
    "$IMAGE" \
    node /app/pdoom-cli.mjs import /dataset.json 2>&1)"
  import_code=$?
  set -e
  if [[ "$import_code" -eq 0 || "$import_logs" != *"synthetic"* ]]; then
    echo "$import_logs" >&2
    echo "production import accepted a synthetic dataset" >&2
    exit 1
  fi
fi

people="$(docker exec "$PG" psql -U pdoom -d pdoom_live -tAc "SELECT count(*) FROM people")"
if [[ "$people" != "0" ]]; then
  echo "production startup loaded ${people} people" >&2
  exit 1
fi

set +e
missing_logs="$(docker run --rm -e NODE_ENV=production -e PDOOM_ENV=production "$IMAGE" 2>&1)"
missing_code=$?
set -e
if [[ "$missing_code" -eq 0 ]]; then
  echo "production start without configuration succeeded" >&2
  exit 1
fi
if [[ "$missing_logs" != *"DATABASE_URL is required"* && "$missing_logs" != *"PDOOM_ENV must be production"* ]]; then
  echo "$missing_logs" >&2
  exit 1
fi

start_ms="$(date +%s%3N)"
docker run -d --name "$WEB" --network "$NET" -p 127.0.0.1:3000:3000 \
  -e NODE_ENV=production \
  -e PDOOM_ENV=production \
  -e APP_BASE_URL=http://127.0.0.1:3000 \
  -e DATABASE_URL=postgresql://pdoom:pdoom@${PG}:5432/pdoom_live \
  -e PDOOM_MIGRATIONS_DIR=/app/migrations \
  -e PORT=3000 \
  -e HOSTNAME=0.0.0.0 \
  "$IMAGE" >/dev/null

live_ok=0
for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:3000/api/live" >/dev/null 2>&1; then
    live_ok=1
    break
  fi
  sleep 1
done
if [[ "$live_ok" != "1" ]]; then
  docker logs "$WEB" >&2 || true
  echo "web process did not become live" >&2
  exit 1
fi
ready_ms="$(date +%s%3N)"
echo "cold_start_ms=$((ready_ms - start_ms))"

curl -fsS "http://127.0.0.1:3000/api/ready" | grep -q '"status":"ready"'
curl -fsS "http://127.0.0.1:3000/api/health" | grep -q '"migrations":"current"'
headers="$(curl -fsS -D - -o /tmp/pdoom-home.html "http://127.0.0.1:3000/")"
printf '%s\n' "$headers" | grep -qi "^content-security-policy:"
printf '%s\n' "$headers" | grep -qi "^x-content-type-options: nosniff"
printf '%s\n' "$headers" | grep -qi "^x-frame-options: DENY"
printf '%s\n' "$headers" | grep -qi "^referrer-policy:"
printf '%s\n' "$headers" | grep -qi "^permissions-policy:"
if printf '%s\n' "$headers" | grep -qi "^strict-transport-security:"; then
  echo "HSTS was set for an http origin" >&2
  exit 1
fi
if grep -q "postgresql://" /tmp/pdoom-home.html; then
  echo "homepage included a database URL" >&2
  exit 1
fi

docker restart "$PG" >/dev/null
for _ in $(seq 1 40); do
  if curl -fsS "http://127.0.0.1:3000/api/ready" | grep -q '"status":"ready"'; then
    echo "postgres_restart=reconnected"
    break
  fi
  sleep 1
done
curl -fsS "http://127.0.0.1:3000/api/ready" | grep -q '"status":"ready"'

docker stats --no-stream --format 'memory={{.MemUsage}} cpu={{.CPUPerc}}' "$WEB"
echo "runtime_smoke_ok"
