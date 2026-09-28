# Disaster recovery

This is the single-VM procedure for pdoom.live. The topology is Caddy, the Next.js web container, and PostgreSQL. There is no Kubernetes cluster, Redis, queue, or cloud control plane.

```text
Internet :80/:443
  -> Caddy
    -> web :3000 on the Docker network
      -> postgres, no host port
```

A backup that remains only on the VM does not survive loss of that VM. Copy every successful backup off the host.

## Host

Use a supported Linux release and install security updates. Create a deploy user that is not root. SSH uses keys. Disable password SSH. The deploy user needs Docker, and membership in the `docker` group is root-equivalent; do not grant it broadly.

The firewall allows inbound 22 from admin addresses, plus 80/tcp and 443/tcp (and 443/udp if HTTP/3 is left enabled). It does not allow inbound 5432. PostgreSQL is attached only to the `pdoom-prod` Docker network.

`/etc/pdoom/production.env` is mode `600` and owned by the deploy user. The directory is mode `0750`. It holds the database password and is not committed. Ubuntu 24.04 Docker install steps, the `docker` group re-login, and the container `pg_dump` command are in the production runbook. Caddy stores certificates in the `pdoom-caddy-data` volume. Do not put private keys or DNS credentials in the repository. `docker compose -f compose.production.yaml down -v` deletes `pdoom-pgdata` and the live database.

Unattended security updates are appropriate for the OS packages. They are not a substitute for reading application releases.

## What is durable

| State | Where it lives | How it is recovered |
| --- | --- | --- |
| Database | volume `pdoom-pgdata` | restore a custom-format `pg_dump` |
| TLS certificates | volume `pdoom-caddy-data` | Caddy requests them again when DNS points at the new VM |
| Application | image `pdoom-live:<git sha>` | rebuild from that commit |
| Canonical dataset | the JSON file you imported | import again, or restore the database backup taken before that import |

Application releases and dataset publication are different operations. A code deploy does not re-import the dataset. A dataset import does not rebuild or restart the web process.

## Release

`deploy/migration-class.tsv` declares each migration `compatible` or `breaking`. A migration missing from that file is breaking. The release script refuses a database that already contains a migration the new image does not have.

| Class | During rollout | Application rollback |
| --- | --- | --- |
| none | No schema change. Candidate is checked before Caddy is reloaded. | Switch back to the previous image. Keep the database. |
| compatible | Previous and new web images can both run. A backup is taken, then migrations run, then the candidate is promoted. | Switch images. Do not restore unless the data itself is wrong. |
| breaking | The previous image may become unready as soon as the migration commits. Pass `--ack-breaking`. | Restore the pre-migration backup, then start the previous image. |

There are no down migrations. `scripts/deploy/rollback.sh` will not invent one.

The candidate is promoted only after `/api/ready` returns 200. Caddy uses that same URL as an active health check, retries an upstream zero times, and gives up after one second. A stopped or unready web process is not served as a successful page.

## Dataset publication

1. `scripts/backup/backup.sh`
2. `scripts/deploy/publish-dataset.sh --file canonical.json`
3. Confirm `dataset_id` and `/api/ready`.

The import runs in one transaction. A failed import leaves the previous rows. An import that commits and is later judged wrong is undone by restoring the pre-import backup, or by importing a corrected canonical file. Import upserts and does not delete rows that are absent from the file, so a corrected file does not by itself remove surplus rows. Use the backup when the bad import added or changed rows you need to erase.

## Backup and retention

`scripts/backup/backup.sh` runs `pg_dump --format=custom` inside the Postgres container, over the local socket, as `POSTGRES_USER`. The official image trusts that socket, so the password is not placed on the command line. The dump is written to a hidden partial name. After `pg_restore --list` succeeds and the file is non-empty, the script checksums it and renames it into place. The manifest records the database name, UTC time, SHA-256, byte size, migration versions, dataset id, and application commit when those are known. It does not record the database URL or password.

`scripts/backup/retain.sh` keeps the newest verified backup for each of the last `PDOOM_BACKUP_KEEP_DAILY` days (at least one day) and, beyond that window, one backup per week for `PDOOM_BACKUP_KEEP_WEEKLY` weeks. `--dry-run` prints deletions and does not remove files. A partial file, a missing manifest, or a checksum mismatch is never deleted.

`PDOOM_BACKUP_HOOK` may be an absolute path of an executable. The script runs that file with the backup directory and the manifest path. It does not pass the value through a shell. An example `rsync` wrapper is `scripts/backup/sync-hook.example`. Install the real wrapper outside the repository.

Suggested cadence, from the deploy user's crontab:

```bash
15 3 * * * cd /opt/pdoom && bash scripts/backup/backup.sh && bash scripts/backup/retain.sh
```

The recovery point is the last backup that was copied off the host. This repository does not promise a formal recovery-time objective. Time a restore with `scripts/restore/drill.sh` on the VM you will actually use; the drill prints `restore_ms` for the dataset it loaded.

## Restore

```bash
bash scripts/restore/restore.sh \
  --backup /var/lib/pdoom/backups/pdoom_live_TIMESTAMP.dump \
  --target-db pdoom_restore_check
```

A new database name is created and loaded. That path does not drop the live database. Replacing an existing database requires `--confirm-replace`. Replacing the production database name also requires `--confirm-production`. The checksum is verified before `pg_restore`. Restore uses one transaction.

## Failure

| What happened | What to do |
| --- | --- |
| New image exits before it is ready | The candidate is removed. The previous container keeps serving. Fix the image and run the release again. |
| Candidate becomes ready, then the recreated web container does not | Caddy stays pointed at the candidate. The release record is not updated. |
| Candidate never becomes ready | It is not promoted. If the release already applied a breaking migration, restore the pre-migration backup before starting the old image. |
| Migration fails | That migration's transaction rolls back and its version is not recorded. The previous web container is still the one Caddy uses. |
| Breaking migration commits, then the new image is bad | `rollback.sh` without a backup refuses to switch. Restore the pre-migration backup, then start the previous image. |
| Dataset import fails | The import transaction rolls back. The pre-import backup is still available. |
| Dataset import commits, then the data is wrong | Restore the pre-import backup, or import a corrected file when surplus rows are acceptable. |
| Disk fills | `scripts/deploy/disk.sh` fails a release below `PDOOM_MIN_FREE_MB`. Retention bounds backups. Image cleanup removes `pdoom-live:<sha>` tags other than the current and previous release. It does not delete those two. |
| VM is gone | Install Docker on a new VM, restore an off-host backup into a new Postgres volume, build `pdoom-live:<sha>` from the recorded commit, start `compose.production.yaml`, and point DNS at the VM. Caddy obtains certificates after port 80 and 443 reach it. |

## Drill

`bash scripts/restore/drill.sh` loads the checked-in live canonical file into a throwaway Postgres container, backs it up, imports a mutated copy, restores the backup, checks counts and migration versions, and checks that a failed import and a failed migration leave the restored data in place. It does not touch `pdoom-pgdata`.
