import { spawnSync } from "node:child_process";
import { chmod, mkdtemp, mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";

function run(command: string, args: string[], env: NodeJS.ProcessEnv = {}) {
  return spawnSync(command, args, {
    encoding: "utf8",
    env: { ...process.env, ...env },
  });
}

async function writeBackup(dir: string, stamp: string, body: string) {
  const database = "pdoom_ops_drill";
  const base = `${database}_${stamp}`;
  const dump = join(dir, `${base}.dump`);
  await writeFile(dump, body);
  const sha = createHash("sha256").update(body).digest("hex");
  await writeFile(join(dir, `${base}.sha256`), `${sha}  ${base}.dump\n`);
  const created = `${stamp.slice(0, 4)}-${stamp.slice(4, 6)}-${stamp.slice(6, 8)}T${stamp.slice(9, 11)}:${stamp.slice(11, 13)}:${stamp.slice(13, 15)}Z`;
  await writeFile(
    join(dir, `${base}.manifest.json`),
    JSON.stringify({
      database,
      created_at: created,
      format: "pg_dump-custom",
      file: `${base}.dump`,
      sha256: sha,
      bytes: Buffer.byteLength(body),
      migrations: ["001_init.sql"],
      app_commit: null,
      dataset_id: "ops-drill",
    }),
  );
}

describe("production operations files", () => {
  it("publishes only Caddy and keeps PostgreSQL off the host", async () => {
    const compose = await readFile("compose.production.yaml", "utf8");
    const caddy = await readFile("deploy/caddy/Caddyfile", "utf8");
    const upstream = await readFile("deploy/caddy/upstream.caddy", "utf8");
    expect(compose).toContain("caddy:2.10-alpine");
    expect(compose).toContain('"80:80"');
    expect(compose).toContain('"443:443"');
    expect(compose).not.toContain("3000:3000");
    expect(compose).not.toContain("5432:5432");
    expect(compose).toContain("max-size: \"10m\"");
    expect(compose).toContain("max-file: \"5\"");
    expect(compose).toContain("pdoom-pgdata");
    expect(compose).toContain("pdoom-caddy-data");
    expect(caddy).toContain("www.pdoom.live");
    expect(caddy).toContain("redir https://pdoom.live{uri} permanent");
    expect(caddy).not.toContain("5432");
    expect(upstream).toContain("health_uri /api/ready");
    expect(upstream).toContain("lb_retries 0");
    expect(upstream).not.toContain("*");
    const ignore = await readFile(".gitignore", "utf8");
    expect(ignore).toContain("!.env.production.example");
    expect(ignore).toContain("deploy/state/");
    const example = await readFile(".env.production.example", "utf8");
    expect(example).toContain("CHANGE_ME");
    expect(example).not.toContain("sk-");
    const docker = await readFile("Dockerfile", "utf8");
    expect(docker).toContain("org.opencontainers.image.revision");
  });

  it("requires acknowledgement for a breaking pending migration and refuses a diverged database", async () => {
    const dir = await mkdtemp(join(tmpdir(), "pdoom-ops-"));
    try {
      await mkdir(join(dir, "migrations"));
      await writeFile(join(dir, "migrations", "001_init.sql"), "-- 001\n");
      await writeFile(join(dir, "migrations", "003_new.sql"), "-- 003\n");
      await writeFile(join(dir, "applied.txt"), "001_init.sql\n");
      const pending = run("bash", [
        "scripts/deploy/classify-migrations.sh",
        join(dir, "migrations"),
        join(dir, "applied.txt"),
        "deploy/migration-class.tsv",
      ]);
      expect(pending.status).toBe(0);
      expect(JSON.parse(pending.stdout)).toMatchObject({ class: "breaking", ack_required: true, pending: ["003_new.sql"] });
      await writeFile(join(dir, "applied.txt"), "001_init.sql\n002_dataset_contract.sql\n");
      await rm(join(dir, "migrations", "003_new.sql"));
      await writeFile(join(dir, "migrations", "002_dataset_contract.sql"), "-- 002\n");
      const current = run("bash", [
        "scripts/deploy/classify-migrations.sh",
        join(dir, "migrations"),
        join(dir, "applied.txt"),
        "deploy/migration-class.tsv",
      ]);
      expect(JSON.parse(current.stdout).class).toBe("none");
      await writeFile(join(dir, "applied.txt"), "001_init.sql\n009_unknown.sql\n");
      const diverged = run("bash", [
        "scripts/deploy/classify-migrations.sh",
        join(dir, "migrations"),
        join(dir, "applied.txt"),
        "deploy/migration-class.tsv",
      ]);
      expect(JSON.parse(diverged.stdout).class).toBe("diverged");
    } finally {
      await rm(dir, { recursive: true, force: true });
    }
  });

  it("rejects the example env file and accepts a mode-600 production file", async () => {
    const example = run("bash", ["scripts/deploy/check-env.sh", ".env.production.example"]);
    expect(example.status).not.toBe(0);
    expect(example.stderr).not.toContain("correct-horse");
    const dir = await mkdtemp(join(tmpdir(), "pdoom-env-"));
    const file = join(dir, "env");
    try {
      await writeFile(
        file,
        [
          "NODE_ENV=production",
          "PDOOM_ENV=production",
          "APP_BASE_URL=https://pdoom.live",
          "PDOOM_WEB_IMAGE=pdoom-live:current",
          "POSTGRES_USER=pdoom",
          "POSTGRES_PASSWORD=correct-horse-battery",
          "POSTGRES_DB=pdoom_live",
          "DATABASE_URL=postgresql://pdoom:correct-horse-battery@postgres:5432/pdoom_live",
          "ACME_EMAIL=ops@pdoom.live",
          "PDOOM_BACKUP_DIR=/var/lib/pdoom/backups",
          "",
        ].join("\n"),
      );
      await chmod(file, 0o600);
      const ok = run("bash", ["scripts/deploy/check-env.sh", file]);
      expect(ok.status).toBe(0);
      expect(ok.stdout).toContain("env file ok");
      expect(ok.stdout).not.toContain("correct-horse-battery");
    } finally {
      await rm(dir, { recursive: true, force: true });
    }
  });

  it("plans image deletion without removing the current or previous release", () => {
    const result = run("bash", ["-c", "printf 'aaaaaaaa\\nbbbbbbbb\\ncurrent\\nprevious\\ncccccccc\\n' | bash scripts/deploy/prune-plan.sh aaaaaaaa bbbbbbbb"]);
    expect(result.status).toBe(0);
    expect(result.stdout.trim().split("\n").filter(Boolean)).toEqual(["cccccccc"]);
  });

  it("keeps the newest verified backups and dry-run does not delete them", async () => {
    const dir = await mkdtemp(join(tmpdir(), "pdoom-backups-"));
    try {
      await writeBackup(dir, "20260920T010000Z", "one");
      await writeBackup(dir, "20260924T010000Z", "two");
      await writeBackup(dir, "20260927T000000Z", "early");
      await writeBackup(dir, "20260927T010000Z", "three");
      await writeFile(join(dir, ".partial.dump"), "partial");
      const dry = run("bash", ["scripts/backup/retain.sh", "--output-dir", dir, "--keep-daily", "1", "--keep-weekly", "0", "--dry-run"]);
      expect(dry.status).toBe(0);
      expect(dry.stdout).toContain("would delete");
      expect(dry.stdout).toContain("pdoom_ops_drill_20260927T000000Z.dump");
      expect(await readFile(join(dir, "pdoom_ops_drill_20260920T010000Z.dump"), "utf8")).toBe("one");
      const real = run("bash", ["scripts/backup/retain.sh", "--output-dir", dir, "--keep-daily", "1", "--keep-weekly", "0"]);
      expect(real.status).toBe(0);
      await expect(readFile(join(dir, "pdoom_ops_drill_20260927T010000Z.dump"), "utf8")).resolves.toBe("three");
      await expect(readFile(join(dir, "pdoom_ops_drill_20260927T000000Z.dump"), "utf8")).rejects.toThrow();
      await expect(readFile(join(dir, "pdoom_ops_drill_20260920T010000Z.dump"), "utf8")).rejects.toThrow();
      expect(await readFile(join(dir, ".partial.dump"), "utf8")).toBe("partial");
    } finally {
      await rm(dir, { recursive: true, force: true });
    }
  });

  it("refuses an application-only rollback after a breaking migration", async () => {
    const dir = await mkdtemp(join(tmpdir(), "pdoom-state-"));
    try {
      await writeFile(
        join(dir, "current.json"),
        JSON.stringify({ commit: "a".repeat(40), image: "pdoom-live:" + "a".repeat(40), migration_class: "breaking" }),
      );
      await writeFile(
        join(dir, "previous.json"),
        JSON.stringify({ commit: "b".repeat(40), image: "pdoom-live:" + "b".repeat(40), migration_class: "none" }),
      );
      const blocked = run("bash", ["scripts/deploy/rollback.sh", "--dry-run"], { PDOOM_STATE_DIR: dir });
      expect(blocked.status).not.toBe(0);
      expect(blocked.stderr).toContain("restore_required");
      await writeFile(
        join(dir, "current.json"),
        JSON.stringify({ commit: "a".repeat(40), image: "pdoom-live:" + "a".repeat(40), migration_class: "none" }),
      );
      const allowed = run("bash", ["scripts/deploy/rollback.sh", "--dry-run"], { PDOOM_STATE_DIR: dir });
      expect(allowed.status).toBe(0);
      expect(allowed.stdout).toContain("preserve_database=yes");
    } finally {
      await rm(dir, { recursive: true, force: true });
    }
  });
});
