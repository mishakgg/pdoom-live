#!/usr/bin/env bash
# Deterministic backup/restore safety tests. Docker is always a scratch fake.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/bin"
cat >"$WORK/bin/date" <<'DATE'
#!/usr/bin/env bash
echo 20261007T000000Z
DATE
cat >"$WORK/bin/mktemp" <<'MKTEMP'
#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${FORCE_IDENTITY:-}" && "$*" == *XXXXXXXX ]]; then
  path="${2%XXXXXXXX}${FORCE_IDENTITY}"
  mkdir "$path"
  echo "$path"
else
  exec /usr/bin/mktemp "$@"
fi
MKTEMP
cat >"$WORK/bin/docker" <<'DOCKER'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >>"$CALL_LOG"
case "$*" in
  *pg_dump*)
    [[ "${FAIL_DUMP:-0}" == 0 ]] || exit 1
    [[ "${SLOW_DUMP:-0}" == 0 ]] || sleep 0.15
    printf '%s\n' "${DUMP_BODY:-valid-scratch-dump}"
    ;;
  *pg_restore*) cat >/dev/null ;;
  *'SELECT version'*) echo 001_init.sql ;;
  *'SELECT dataset_id'*) echo test-dataset ;;
  *'SELECT 1 FROM pg_database'*) echo 1 ;;
esac
DOCKER
cat >"$WORK/hook" <<'HOOK'
#!/usr/bin/env bash
set -eu
echo "$2" >>"$HOOK_LOG"
echo hook-ran
HOOK
chmod +x "$WORK/bin/"* "$WORK/hook"
cat >"$WORK/env" <<ENV
NODE_ENV=production
PDOOM_ENV=production
APP_BASE_URL=https://pdoom.live
PDOOM_WEB_IMAGE=pdoom-live:current
POSTGRES_USER=custom_user
POSTGRES_PASSWORD=backup-safety-test-password
POSTGRES_DB=custom_db
DATABASE_URL=postgresql://custom_user:backup-safety-test-password@postgres:5432/custom_db
ACME_EMAIL=ops@pdoom.live
PDOOM_BACKUP_DIR=$WORK/configured-backups
PDOOM_BACKUP_KEEP_DAILY=1
PDOOM_BACKUP_KEEP_WEEKLY=0
PDOOM_BACKUP_HOOK=$WORK/hook
ENV
chmod 600 "$WORK/env"
export PATH="$WORK/bin:$PATH" PDOOM_ENV_FILE="$WORK/env" CALL_LOG="$WORK/calls" HOOK_LOG="$WORK/hooks"
unset PDOOM_OPS_ENV_MODE
fail() { echo "backup safety test failed: $*" >&2; exit 1; }
expect_fail() { if "$@" >"$WORK/failure-output" 2>&1; then fail "unexpected success"; fi; }

# File mode reads custom DB/user/path/hook; stdout is only the resulting archive.
first="$(umask 022; FORCE_IDENTITY=COLLIDE1 bash "$ROOT/scripts/backup/backup.sh" 2>"$WORK/hook-output")"
test -f "$first"
[[ "$first" == "$WORK/configured-backups/"* ]] || fail "configured directory ignored"
grep -q -- 'pg_dump --username custom_user .*--dbname custom_db' "$CALL_LOG"
grep -q 'COLLIDE1.manifest.json' "$HOOK_LOG"
[[ "$(stat -c %a "$first")" == 600 ]] || fail "dump is not private"
[[ "$(stat -c %a "${first%.dump}.sha256")" == 600 ]] || fail "checksum is not private"
[[ "$(stat -c %a "${first%.dump}.manifest.json")" == 600 ]] || fail "manifest is not private"
[[ "$(stat -c %a "$WORK/configured-backups")" == 700 ]] || fail "new directory is not private"
sha256sum "$first" "${first%.dump}.sha256" "${first%.dump}.manifest.json" >"$WORK/original-hashes"

# Failed same-second retry must never clean up files owned by the first run.
expect_fail env FORCE_IDENTITY=COLLIDE1 FAIL_DUMP=1 bash "$ROOT/scripts/backup/backup.sh"
sha256sum -c "$WORK/original-hashes" >/dev/null
# A successful dump with a colliding final identity must also refuse overwrite.
expect_fail env FORCE_IDENTITY=COLLIDE1 DUMP_BODY=replacement bash "$ROOT/scripts/backup/backup.sh"
sha256sum -c "$WORK/original-hashes" >/dev/null

# A directory or directory symlink at the final name is an exact-path collision,
# never an invitation to create an archive inside that directory.
directory_collision="$WORK/configured-backups/custom_db_20261007T000000Z.DIRECTORY.dump"
mkdir "$directory_collision"
echo keep >"$directory_collision/sentinel"
expect_fail env FORCE_IDENTITY=DIRECTORY bash "$ROOT/scripts/backup/backup.sh"
[[ "$(cat "$directory_collision/sentinel")" == keep ]] || fail "directory collision changed"
test ! -e "$directory_collision/archive.dump"
mkdir "$WORK/symlink-target"
ln -s "$WORK/symlink-target" "$WORK/configured-backups/custom_db_20261007T000000Z.SYMLINK.dump"
expect_fail env FORCE_IDENTITY=SYMLINK bash "$ROOT/scripts/backup/backup.sh"
test -L "$WORK/configured-backups/custom_db_20261007T000000Z.SYMLINK.dump"
test ! -e "$WORK/symlink-target/archive.dump"
# Remove only these scratch collision fixtures before retention inspects archives.
rm "$WORK/configured-backups/custom_db_20261007T000000Z.SYMLINK.dump"
rm -r "$directory_collision"

# Two overlapping successful backups with a fixed timestamp have distinct triples.
SLOW_DUMP=1 bash "$ROOT/scripts/backup/backup.sh" >"$WORK/one" 2>"$WORK/one-err" &
pid_one=$!
SLOW_DUMP=1 bash "$ROOT/scripts/backup/backup.sh" >"$WORK/two" 2>"$WORK/two-err" &
pid_two=$!
wait "$pid_one"
wait "$pid_two"
[[ "$(cat "$WORK/one")" != "$(cat "$WORK/two")" ]] || fail "concurrent identities collide"
for file in "$first" "$(cat "$WORK/one")" "$(cat "$WORK/two")"; do
  (cd "$(dirname "$file")" && sha256sum -c "$(basename "${file%.dump}.sha256")") >/dev/null
  test -f "${file%.dump}.manifest.json"
done
[[ "$(find "$WORK/configured-backups" -mindepth 1 -maxdepth 1 -type d | wc -l)" == 0 ]] || fail "staging directory leaked"

# A failing overlapping invocation must not remove the successful run's files.
SLOW_DUMP=1 bash "$ROOT/scripts/backup/backup.sh" >"$WORK/survivor" 2>/dev/null &
survivor_pid=$!
FAIL_DUMP=1 bash "$ROOT/scripts/backup/backup.sh" >"$WORK/failed" 2>/dev/null &
failed_pid=$!
wait "$survivor_pid"
if wait "$failed_pid"; then fail "concurrent failing dump succeeded"; fi
survivor="$(cat "$WORK/survivor")"
(cd "$(dirname "$survivor")" && sha256sum -c "$(basename "${survivor%.dump}.sha256")") >/dev/null
sha256sum -c "$WORK/original-hashes" >/dev/null

# CLI values override the validated env file; hook stdout cannot contaminate paths.
override="$(bash "$ROOT/scripts/backup/backup.sh" --database cli_db --username cli_user --output-dir "$WORK/cli" --hook '' 2>/dev/null)"
[[ "$override" == "$WORK/cli/cli_db_"* ]] || fail "CLI did not override defaults"
grep -q -- 'pg_dump --username cli_user .*--dbname cli_db' "$CALL_LOG"

# Retention must use configured directory and bounds without CLI arguments.
bash "$ROOT/scripts/backup/retain.sh" --dry-run >"$WORK/retention"
grep -q 'would delete custom_db_' "$WORK/retention"

# Actual configured production name requires BOTH confirmations before dropping.
: >"$CALL_LOG"
expect_fail bash "$ROOT/scripts/restore/restore.sh" --backup "$first" --target-db custom_db --confirm-replace
grep -q 'without --confirm-production' "$WORK/failure-output"
! grep -q dropdb "$CALL_LOG"
bash "$ROOT/scripts/restore/restore.sh" --backup "$first" --target-db custom_db --confirm-replace --confirm-production >/dev/null
grep -q -- 'dropdb --username custom_user --force custom_db' "$CALL_LOG"

# Shell expressions are data that must be rejected before any Docker invocation.
cp "$WORK/env" "$WORK/hostile-env"
printf 'PDOOM_BACKUP_HOOK=$(touch %s)\n' "$WORK/should-not-exist" >>"$WORK/hostile-env"
: >"$CALL_LOG"
expect_fail env PDOOM_ENV_FILE="$WORK/hostile-env" bash "$ROOT/scripts/backup/backup.sh"
test ! -e "$WORK/should-not-exist"
test ! -s "$CALL_LOG"
expect_fail env PDOOM_ENV_FILE="$WORK/missing" bash "$ROOT/scripts/backup/backup.sh"

# Explicit process mode supports a throwaway drill without consulting production.
process="$(PDOOM_OPS_ENV_MODE=process POSTGRES_DB=drill_db POSTGRES_USER=drill_user PDOOM_BACKUP_DIR="$WORK/drill" PDOOM_BACKUP_HOOK='' PDOOM_ENV_FILE="$WORK/missing" bash "$ROOT/scripts/backup/backup.sh")"
[[ "$process" == "$WORK/drill/drill_db_"* ]] || fail "process mode failed"
! grep -q 'backup-safety-test-password' "$WORK/hook-output"
printf 'backup_safety_test_ok\n'
