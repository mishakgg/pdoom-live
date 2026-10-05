#!/usr/bin/env bash
# Wait until a fresh official Postgres container has finished entrypoint init.
# pg_isready succeeds on the temporary init server, then fails while it restarts.
set -euo pipefail
set +x

container="${1:-}"
db_user="${2:-}"
database="${3:-}"
attempts="${PDOOM_POSTGRES_READY_ATTEMPTS:-40}"
interval="${PDOOM_POSTGRES_READY_INTERVAL:-1}"

if [[ -z "$container" || -z "$db_user" || -z "$database" ]]; then
  echo "usage: postgres-ready.sh CONTAINER USER DATABASE" >&2
  exit 1
fi
[[ "$container" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]+$ ]] || { echo "container name is invalid" >&2; exit 1; }
[[ "$db_user" =~ ^[A-Za-z][A-Za-z0-9_]{0,62}$ ]] || { echo "database user is invalid" >&2; exit 1; }
[[ "$database" =~ ^[A-Za-z][A-Za-z0-9_]{0,62}$ ]] || { echo "database name is invalid" >&2; exit 1; }
[[ "$attempts" =~ ^[1-9][0-9]*$ ]] || { echo "ready attempts are invalid" >&2; exit 1; }
[[ "$interval" =~ ^[0-9]+$ ]] || { echo "ready interval is invalid" >&2; exit 1; }

for _ in $(seq 1 "$attempts"); do
  logs="$(docker logs "$container" 2>/dev/null || true)"
  case "$logs" in
    *"PostgreSQL init process complete"*)
      if docker exec "$container" pg_isready -U "$db_user" -d "$database" >/dev/null 2>&1; then
        exit 0
      fi
      ;;
  esac
  sleep "$interval"
done

echo "postgres did not become ready after its init server restarted" >&2
exit 1
