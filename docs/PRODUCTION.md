# Production runbook

pdoom.live in production is a Next.js server and PostgreSQL. Migrations, dataset import, and web startup are three separate steps. The web process does not migrate, import, seed, or reset when it starts.

The image does not include Redis, a queue, a crawler, or a vector database. Local `npm run dev` does not need Docker.

## Required configuration

Set these for every production process, including one-off migrate and import commands:

| Variable | Required | Purpose |
| --- | --- | --- |
| `NODE_ENV` | yes | `production` |
| `PDOOM_ENV` | yes | `production` |
| `DATABASE_URL` | yes | Postgres URL with a database name. Never printed in logs or health responses. |
| `APP_BASE_URL` | yes | Public origin only, such as `https://pdoom.example` or `http://127.0.0.1:3000`. No userinfo, path, query, or fragment. |

Optional:

| Variable | Purpose |
| --- | --- |
| `PORT` | Web port. Default `3000`. |
| `HOSTNAME` | Bind address inside the container. The image sets `0.0.0.0`. |
| `PDOOM_MIGRATIONS_DIR` | Directory of SQL migrations. The image sets `/app/migrations`. |
| `PDOOM_HSTS` | `on` or `off`. When unset, HSTS is sent only if `APP_BASE_URL` is `https`. |
| `OPENAI_API_KEY` | Unused by the web process. If set, it must be non-empty and is not logged. |

Unknown `PDOOM_*` variables are rejected. Empty optional values are rejected. Production refuses `PDOOM_IMPORT_HOLD` and `PDOOM_FIXTURE_PATH`.

The web process exits immediately when required configuration is missing or invalid. The log line names the problem and does not print secret values, database URLs, or stack traces.

`https` origins send `Strict-Transport-Security: max-age=15552000` and CSP `upgrade-insecure-requests`. Plain `http` origins do not. Set `PDOOM_HSTS=on` only when clients actually reach the site over TLS, including TLS terminated in front of the container. Set `PDOOM_HSTS=off` to suppress both headers.

The compose file's database password is for a local project. Change it before the database port is reachable beyond the host.

## Initialization order

1. Start PostgreSQL and keep its data volume.
2. Run migrations.
3. Import a canonical dataset file, if you have one.
4. Start the web process.

An empty migrated database is a valid ready state. The web process will not load `data/fixtures/synthetic/dataset.json`. `db:seed` and `db:reset` exit with an error in production. Importing a document with `dataset_kind: synthetic` also exits with an error.

Import upserts rows and keeps rows that are absent from the file. It does not truncate. Take a backup before an import you may need to undo.

## Commands

Docker Compose, from the repository root:

```bash
docker compose build
docker compose up -d postgres
docker compose run --rm web node /app/pdoom-cli.mjs migrate
docker compose run --rm -v "$PWD/canonical.json:/dataset.json:ro" web \
  node /app/pdoom-cli.mjs import /dataset.json
docker compose up -d web
docker compose ps
curl -fsS http://127.0.0.1:3000/api/ready
docker compose stop
```

`docker compose stop` and `docker compose down` keep the `pgdata` volume. `docker compose down -v` deletes that volume.

Without Compose, on a host that already has Node 22 and PostgreSQL:

```bash
npm ci
npm run build
npm run build:cli
export NODE_ENV=production PDOOM_ENV=production
export APP_BASE_URL=https://pdoom.example
export DATABASE_URL=postgresql://pdoom:password@127.0.0.1:5432/pdoom_live
export PDOOM_MIGRATIONS_DIR="$PWD/packages/db/migrations"
node dist/pdoom-cli.mjs migrate
node dist/pdoom-cli.mjs import /var/lib/pdoom/canonical.json
npm run start
```

`npm run db:migrate`, `npm run db:import -- <file>`, and `npm run db:status` are the same commands through `tsx` and are appropriate on a checkout. `db:status` does not migrate or import.

## Health

| URL | Meaning | HTTP |
| --- | --- | --- |
| `/api/live` | The process can answer. It does not check PostgreSQL. | 200 |
| `/api/ready` | Process is up, PostgreSQL answered, and applied migrations match this build. | 200 or 503 |
| `/api/health` | Same report as `/api/ready`. | 200 or 503 |

Ready body:

```json
{"status":"ready","checks":{"process":"live","database":"ok","migrations":"current"}}
```

`migrations` is `pending` when this build has a migration the database lacks, and `diverged` when the database has a migration this build does not. Either one, or a database outage, is `not_ready`. Responses do not include SQL text, connection strings, filesystem paths, stack traces, or environment dumps.

The image health check calls `/api/ready`. Docker does not restart a container merely because that check fails. `restart: unless-stopped` brings the process back after a crash or a host reboot.

Other routes return 503 until the app is ready, so a half-migrated schema is not served. `/api/live`, `/api/ready`, and `/api/health` stay available.

## Shutdown, migrations, and database restarts

The container runs as user `pdoom` under `tini`, so PID 1 forwards `SIGTERM` and reaps child processes. The web server closes its PostgreSQL pool on `SIGTERM` and `SIGINT`. Web queries are short. A dropped connection does not leave a partial page write in the database.

`migrate` and `import` take a session advisory lock and run inside transactions. A second migrate exits with `migration already in progress` and does not apply files. A failed migration rolls back that file, does not record its version, and exits non-zero. Readiness stays `pending`.

`SIGTERM` during import sets an abort flag, cancels the active backend, and rolls back before commit. Run the import again. Imports are idempotent upserts.

The web pool uses a small set of connections (`max: 5`), a 15 second statement timeout, and TCP keepalives. If PostgreSQL restarts, the pool discards the dead connection and the next query opens a new one. Readiness tries once more after a failed ping. One request may fail during the restart. The process keeps running.

CLI migrate and import use a 120 second statement timeout so a larger migration is not cut off by the web timeout.

## Security headers

Responses from the Node proxy include:

- `Content-Security-Policy`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `X-Frame-Options: DENY`
- `Permissions-Policy` disabling camera, microphone, geolocation, payment, and USB
- `Strict-Transport-Security` only when HSTS is enabled, as described above

Production CSP allows same-origin resources, a per-request script and style nonce, and `strict-dynamic` for scripts Next.js loads from that nonce. `frame-ancestors 'none'` and `frame-src 'none'` block framing. `script-src-attr 'none'` blocks inline event handlers. This build applies font variables through stylesheets, so production does not allow `'unsafe-inline'` for styles or style attributes. Development adds `'unsafe-eval'` for React debugging and allows inline style elements.

Static files under `/_next/static` receive the non-CSP headers from `next.config.ts`.

## Backup, deploy, and rollback

PostgreSQL is the only stateful component. The canonical JSON file is the import source; the database is what the site serves. Back up before migrate or import.

```bash
pg_dump -Fc -h 127.0.0.1 -U pdoom -d pdoom_live -f pdoom.dump
```

Restore with the web process stopped:

```bash
docker compose stop web
pg_restore --clean --if-exists -h 127.0.0.1 -U pdoom -d pdoom_live pdoom.dump
docker compose start web
curl -fsS http://127.0.0.1:3000/api/ready
```

`--clean` drops objects before recreating them. Use it only against the database you intend to replace.

Deploy on a small VM:

1. Build or pull the new image.
2. Dump the database.
3. Start the new image's migrate command against that database. The previous web process can stay up; migrate takes an advisory lock and the old process does not migrate.
4. If migrate succeeds, restart the web container so it serves the new build.
5. Check `/api/ready`, then `/api/live`.

Migrations are forward-only. There is no down migration. If the new build applied a migration the previous image does not contain, the previous image reports `migrations: diverged` and will not serve traffic. Restore the pre-migrate dump, then start the previous image. If the migration was compatible and only the web code is bad, restart the previous image without restoring.

Prefer a private network or `sslmode=verify-full` for a database that is not on localhost. The local compose network is not TLS.

## Checks

`bash scripts/runtime-smoke.sh pdoom-live:ci` builds the image when it is missing, migrates a throwaway database, proves production seed and synthetic import are refused, and curls liveness, readiness, and security headers. GitHub Actions runs that script on `ubuntu-latest` with a read-only checkout token. Fork pull requests do not receive deployment credentials, write tokens, or a production database. Workflows do not use `pull_request_target` or self-hosted runners.

Image size, idle memory, and cold start depend on the host. Inspect a local image with:

```bash
docker image inspect pdoom-live:ci --format '{{.Size}}'
docker stats --no-stream
```

The Next.js production build is the standalone output copied into the runtime image. Dev dependencies and the collector tree are not in that image.
