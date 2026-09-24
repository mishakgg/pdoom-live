import { readdir, readFile } from "node:fs/promises";
import type pg from "pg";
import { migrationsDir } from "./paths";

export async function migrate(pool: pg.Pool): Promise<string[]> {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS schema_migrations (
      version text PRIMARY KEY,
      applied_at timestamptz NOT NULL DEFAULT now()
    )
  `);
  const files = (await readdir(migrationsDir)).filter((file) => file.endsWith(".sql")).sort();
  const applied: string[] = [];
  for (const file of files) {
    const existing = await pool.query("SELECT 1 FROM schema_migrations WHERE version = $1", [file]);
    if (existing.rowCount) continue;
    const sql = await readFile(`${migrationsDir}/${file}`, "utf8");
    const client = await pool.connect();
    try {
      await client.query("BEGIN");
      await client.query(sql);
      await client.query("INSERT INTO schema_migrations (version) VALUES ($1)", [file]);
      await client.query("COMMIT");
      applied.push(file);
    } catch (error) {
      await client.query("ROLLBACK");
      throw error;
    } finally {
      client.release();
    }
  }
  return applied;
}
