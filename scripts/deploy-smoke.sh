#!/usr/bin/env bash
# Read-only check for a deployed pdoom.live web process.
# GET requests only. It does not change the database or rerun schema commands.
set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "usage: scripts/deploy-smoke.sh [base-url]" >&2
  echo "default base URL: http://127.0.0.1:3000" >&2
  exit 0
fi

BASE="${1:-http://127.0.0.1:3000}"
BASE="${BASE%/}"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

fetch() {
  local path="$1"
  local code
  code="$(curl -sS --max-time 30 -D "$WORKDIR/headers" -o "$WORKDIR/body" -w '%{http_code}' "$BASE$path")" || {
    echo "smoke_fail: GET $path failed" >&2
    exit 1
  }
  printf '%s' "$code"
}

require_status() {
  local path="$1"
  local expect="$2"
  local code
  code="$(fetch "$path")"
  if [[ "$code" != "$expect" ]]; then
    echo "smoke_fail: $path returned $code, expected $expect" >&2
    exit 1
  fi
}

require_header() {
  local name="$1"
  local pattern="$2"
  if ! grep -Eiq "^${name}: ${pattern}" "$WORKDIR/headers"; then
    echo "smoke_fail: $path missing header ${name}" >&2
    exit 1
  fi
}

reject_secrets() {
  if grep -Eiq 'postgres(ql)?://' "$WORKDIR/body"; then
    echo "smoke_fail: $path response contains a database URL" >&2
    exit 1
  fi
}

require_security_headers() {
  require_header 'content-security-policy' '.*'
  require_header 'x-content-type-options' 'nosniff'
  require_header 'referrer-policy' 'strict-origin-when-cross-origin'
  require_header 'x-frame-options' 'DENY'
  require_header 'permissions-policy' 'camera=\(\).*microphone=\(\).*geolocation=\(\).*payment=\(\).*usb=\(\)'
}

path=/api/live
require_status /api/live 200
grep -q '"status":"live"' "$WORKDIR/body" || {
  echo "smoke_fail: /api/live body" >&2
  exit 1
}
reject_secrets

path=/api/ready
require_status /api/ready 200
grep -q '"status":"ready"' "$WORKDIR/body" || {
  echo "smoke_fail: /api/ready status" >&2
  exit 1
}
grep -q '"database":"ok"' "$WORKDIR/body" || {
  echo "smoke_fail: /api/ready database" >&2
  exit 1
}
grep -q '"migrations":"current"' "$WORKDIR/body" || {
  echo "smoke_fail: /api/ready migrations" >&2
  exit 1
}
require_security_headers
reject_secrets

path=/api/health
require_status /api/health 200
grep -q '"status":"ready"' "$WORKDIR/body" || {
  echo "smoke_fail: /api/health body" >&2
  exit 1
}
reject_secrets

for path in / /people /statements /topics /trends /sources /methodology; do
  require_status "$path" 200
  require_security_headers
  reject_secrets
done

path=/
require_status / 200
grep -q 'Live dataset' "$WORKDIR/body" || {
  echo "smoke_fail: home page is not serving a live dataset" >&2
  exit 1
}
if grep -q '<strong>Synthetic fixture</strong>' "$WORKDIR/body"; then
  echo "smoke_fail: synthetic fixture is being served" >&2
  exit 1
fi
grep -Eq '[1-9][0-9]*(<!-- -->)? tracked people' "$WORKDIR/body" || {
  echo "smoke_fail: home page has no tracked people" >&2
  exit 1
}

path=/people
require_status /people 200
grep -q 'href="/people/' "$WORKDIR/body" || {
  echo "smoke_fail: people page has no database-backed person links" >&2
  exit 1
}

echo "deploy_smoke_ok ${BASE}"
