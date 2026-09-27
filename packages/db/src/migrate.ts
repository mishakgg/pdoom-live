import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import type pg from "pg";
import { migrationsDirectory } from "./paths";

export const MIGRATION_LOCK_KEYS = [81420721, 20260927] as const;

export type MigrationStatus = "current" | "pending" | "diverged";

async function listMigrationFiles(directory: string): Promise<string[]> {
  const files = (await readdir(directory)).filter((file) => file.endsWith(".sql") && !file.includes("/"));
  files.sort();
  return files;
}

export async function migrationState(pool: pg.Pool, directory = migrationsDirectory()): Promise<MigrationStatus> {
  const files = await listMigrationFiles(directory);
  const reg = await pool.query<{ name: string | null }>("SELECT to_regclass('public.schema_migrations') AS name");
  if (!reg.rows[0]?.name) return files.length === 0 ? "current" : "pending";
  const applied = await pool.query<{ version: string }>("SELECT version FROM schema_migrations");
  const have = new Set(applied.rows.map((row) => row.version));
  for (const file of files) {
    if (!have.has(file)) return "pending";
  }
  for (const version of have) {
    if (!files.includes(version)) return "diverged";
  }
  return "current";
}

export async function migrate(pool: pg.Pool, options: { directory?: string } = {}): Promise<string[]> {
  const directory = options.directory ?? migrationsDirectory();
  const files = await listMigrationFiles(directory);
  const client = await pool.connect();
  let locked = false;
  try {
    const lock = await client.query<{ locked: boolean }>(
      "SELECT pg_try_advisory_lock($1::int, $2::int) AS locked",
      [...MIGRATION_LOCK_KEYS],
    );
    if (lock.rows[0]?.locked !== true) {
      throw new Error("migration already in progress");
    }
    locked = true;
    await client.query(`
      CREATE TABLE IF NOT EXISTS schema_migrations (
        version text PRIMARY KEY,
        applied_at timestamptz NOT NULL DEFAULT now()
      )
    `);
    const applied: string[] = [];
    for (const file of files) {
      const existing = await client.query("SELECT 1 FROM schema_migrations WHERE version = $1", [file]);
      if (existing.rowCount) continue;
      const sql = await readFile(join(directory, file), "utf8");
      try {
        await client.query("BEGIN");
        await client.query(sql);
        await client.query("INSERT INTO schema_migrations (version) VALUES ($1)", [file]);
        await client.query("COMMIT");
        applied.push(file);
      } catch (error) {
        await client.query("ROLLBACK").catch(() => undefined);
        const detail = error instanceof Error ? error.message.replace(/postgres(ql)?:\/\/\S+/gi, "[redacted]") : "failed";
        throw new Error(`migration ${file} failed: ${detail.slice(0, 300)}`);
      }
    }
    return applied;
  } finally {
    if (locked) {
      await client.query("SELECT pg_advisory_unlock($1::int, $2::int)", [...MIGRATION_LOCK_KEYS]).catch(() => undefined);
    }
    client.release();
  }
}
