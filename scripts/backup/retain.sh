#!/usr/bin/env bash
# Keep recent daily backups and a bounded set of older weekly snapshots.
# Incomplete or unverified backups are never deleted.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=../deploy/lib.sh
source "$HERE/../deploy/lib.sh"
require_cmd python3

output_dir="${PDOOM_BACKUP_DIR:-/var/lib/pdoom/backups}"
keep_daily="${PDOOM_BACKUP_KEEP_DAILY:-14}"
keep_weekly="${PDOOM_BACKUP_KEEP_WEEKLY:-8}"
dry_run=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir) output_dir="$2"; shift 2 ;;
    --keep-daily) keep_daily="$2"; shift 2 ;;
    --keep-weekly) keep_weekly="$2"; shift 2 ;;
    --dry-run) dry_run=1; shift ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ "$keep_daily" =~ ^[0-9]+$ && "$keep_daily" -ge 1 ]] || die "keep-daily must be at least 1"
[[ "$keep_weekly" =~ ^[0-9]+$ ]] || die "keep-weekly must be a number"
[[ -d "$output_dir" ]] || die "backup directory is missing"

python3 - "$output_dir" "$keep_daily" "$keep_weekly" "$dry_run" <<'PY'
import hashlib, json, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

directory = Path(sys.argv[1])
keep_daily = int(sys.argv[2])
keep_weekly = int(sys.argv[3])
dry_run = sys.argv[4] == "1"

def verified(dump: Path):
    checksum = dump.with_suffix(".sha256")
    manifest = dump.with_name(dump.name.replace(".dump", ".manifest.json"))
    if not checksum.is_file() or not manifest.is_file():
        return None
    line = checksum.read_text().strip().split()
    if len(line) < 2 or line[1] != dump.name:
        return None
    digest = hashlib.sha256(dump.read_bytes()).hexdigest()
    if digest != line[0]:
        return None
    meta = json.loads(manifest.read_text())
    if meta.get("sha256") != digest or meta.get("file") != dump.name:
        return None
    created = datetime.strptime(meta["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return created, manifest, checksum

complete = []
for dump in sorted(directory.glob("*.dump")):
    if dump.name.startswith("."):
        continue
    checked = verified(dump)
    if checked is None:
        print(f"keep incomplete {dump.name}")
        continue
    complete.append((checked[0], dump, checked[1], checked[2]))

complete.sort(key=lambda item: item[0])
if not complete:
    print("no verified backups")
    raise SystemExit(0)

newest_by_day = {}
for item in complete:
    day = item[0].date()
    current = newest_by_day.get(day)
    if current is None or item[0] >= current[0]:
        newest_by_day[day] = item

newest_day = complete[-1][0].date()
daily_days = {newest_day - timedelta(days=offset) for offset in range(keep_daily)}
keep = set()
for day, item in newest_by_day.items():
    if day in daily_days:
        keep.add(item[1])

weekly_kept = 0
seen_weeks = set()
cutoff = newest_day - timedelta(days=keep_daily - 1)
for created, dump, _manifest, _checksum in reversed(complete):
    if dump in keep or created.date() >= cutoff:
        continue
    week = created.strftime("%G-W%V")
    if week in seen_weeks:
        continue
    if weekly_kept >= keep_weekly:
        continue
    seen_weeks.add(week)
    keep.add(dump)
    weekly_kept += 1

# The newest verified backup is always kept.
keep.add(complete[-1][1])

for created, dump, manifest, checksum in complete:
    if dump in keep:
        print(f"keep {dump.name}")
        continue
    print(f"{'would delete' if dry_run else 'delete'} {dump.name}")
    if not dry_run:
        dump.unlink()
        manifest.unlink()
        checksum.unlink()
PY
