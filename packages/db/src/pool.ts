import pg from "pg";
import { readDatabaseUrl } from "./env";

const { Pool } = pg;

let pool: pg.Pool | null = null;

export function createPool(connectionString: string): pg.Pool {
  return new Pool({
    connectionString,
    max: 5,
    statement_timeout: 15_000,
  });
}

export function getPool(): pg.Pool {
  if (!pool) {
    pool = createPool(readDatabaseUrl("DATABASE_URL"));
  }
  return pool;
}

export async function closePool(): Promise<void> {
  if (pool) {
    await pool.end();
    pool = null;
  }
}
