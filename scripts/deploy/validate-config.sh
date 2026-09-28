#!/usr/bin/env bash
# Render the production compose file and reject a published database port.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
command -v docker >/dev/null
command -v python3 >/dev/null
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
cat >"$work/env" <<'EOF'
NODE_ENV=production
PDOOM_ENV=production
APP_BASE_URL=https://pdoom.live
PDOOM_WEB_IMAGE=pdoom-live:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
POSTGRES_USER=pdoom
POSTGRES_PASSWORD=correct-horse-battery
POSTGRES_DB=pdoom_live
DATABASE_URL=postgresql://pdoom:correct-horse-battery@postgres:5432/pdoom_live
ACME_EMAIL=ops@pdoom.live
PDOOM_BACKUP_DIR=/var/lib/pdoom/backups
GIT_COMMIT=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
BUILD_TIME=2026-09-27T00:00:00Z
EOF
chmod 600 "$work/env"
mkdir -p "$ROOT/deploy/state"
if [[ ! -f "$ROOT/deploy/state/upstream.caddy" ]]; then
  cp "$ROOT/deploy/caddy/upstream.caddy" "$ROOT/deploy/state/upstream.caddy"
fi
docker compose --env-file "$work/env" -f "$ROOT/compose.production.yaml" config --format json >"$work/config.json"
python3 - "$work/config.json" <<'PY'
import json, sys
document = json.load(open(sys.argv[1], encoding="utf-8"))
services = document["services"]
for name in ("caddy", "web", "postgres"):
    if name not in services:
        sys.exit(f"missing service {name}")
postgres_ports = services["postgres"].get("ports") or []
web_ports = services["web"].get("ports") or []
caddy_ports = services["caddy"].get("ports") or []
if postgres_ports or web_ports:
    sys.exit("postgres or web publishes a host port")
published = set()
for port in caddy_ports:
    published.add(str(port.get("published")))
    if port.get("target") not in (80, 443, "80", "443"):
        sys.exit(f"unexpected caddy target port {port}")
if "80" not in published or "443" not in published:
    sys.exit(f"caddy ports are {sorted(published)}")
for name, service in services.items():
    logging = service.get("logging") or {}
    options = logging.get("options") or {}
    if options.get("max-size") != "10m" or options.get("max-file") != "5":
        sys.exit(f"{name} is missing log rotation")
print("compose_config_ok")
PY
